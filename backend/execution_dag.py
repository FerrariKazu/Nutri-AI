"""
Nutri Execution DAG (Parallel Execution Engine)

This module implements a dependency-graph based scheduler for executing Nutri agents.
It enables parallel execution of independent tasks (e.g., Nutrition Analysis running alongside Sensory Modeling)
and manages the lifecycle of speculative and luxury tasks.
"""

import asyncio
import logging
import time
from typing import Dict, Set, List, Any, Callable, Optional, Awaitable, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class AgentNode:
    """Represents a single executable task in the dependency graph."""
    name: str
    func: Callable[..., Awaitable[Any]]  # Must be an async function
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    depends_on: Set[str] = field(default_factory=set)
    is_luxury: bool = False      # If true, can be cancelled under load
    is_speculative: bool = False # If true, runs early and might be discarded
    priority: int = 10           # Higher = runs sooner if resources constrained

@dataclass
class NodeResult:
    """Result container for a node execution."""
    name: str
    result: Any
    duration: float
    error: Optional[Exception] = None
    cancelled: bool = False

class DAGScheduler:
    """
    Manages the execution of AgentNodes based on their dependencies.
    Optimizes for parallelism and perceived latency.
    """
    
    def __init__(self):
        self.nodes: Dict[str, AgentNode] = {}
        self.results: Dict[str, NodeResult] = {}
        self.futures: Dict[str, asyncio.Future] = {}
        self._cancellation_tokens: Dict[str, asyncio.Event] = {}
        self._running_tasks: Set[asyncio.Task] = set()

    def add_node(self, node: AgentNode):
        """Register a node in the graph."""
        if node.name in self.nodes:
            logger.warning(f"Overwriting existing node {node.name}")
        self.nodes[node.name] = node

    async def execute(self, execution_policy: Any = None) -> Dict[str, Any]:
        """
        Execute the graph.
        
        Args:
            execution_policy: Optional ExecutionPolicy to filter/enable nodes.
                              (Not fully enforced here yet, relies on Orchestrator config)
        
        Returns:
            Dictionary of results map {node_name: result_content}
        """
        start_time = time.time()
        logger.info(f"DAG Execution started with {len(self.nodes)} nodes")
        
        # Reset state
        self.results = {}
        self.futures = {name: asyncio.Future() for name in self.nodes}
        
        # Identify ready nodes (no dependencies)
        ready_nodes = [name for name, node in self.nodes.items() if not node.depends_on]
        
        if not ready_nodes and self.nodes:
            logger.error("Circular dependency detected or no start nodes!")
            return {}

        # Launch initial batch
        # We need a continuous loop or a mechanism to trigger downstream tasks
        # Simpler approach: Launch tasks that wait for their dependencies
        
        # PYTHON 3.10 COMPATIBILITY FIX: Replaced TaskGroup with manual set management
        tasks = set()
        for name, node in self.nodes.items():
            task = asyncio.create_task(self._run_node_wrapper(name, node))
            tasks.add(task)
            self._running_tasks.add(task)
            task.add_done_callback(tasks.discard)
            task.add_done_callback(self._running_tasks.discard)
            
        if tasks:
            await asyncio.gather(*tasks)
                
        # Aggregate results (unwrap from NodeResult)
        final_output = {}
        for name, res in self.results.items():
            if res.error:
                logger.error(f"Node {name} failed: {res.error}")
                # We could choose to propagate error or just omit
                final_output[name] = {"error": str(res.error)}
            elif not res.cancelled:
                final_output[name] = res.result
                
        duration = time.time() - start_time
        logger.info(f"DAG Execution completed in {duration:.2f}s")
        return final_output

    async def _run_node_wrapper(self, name: str, node: AgentNode):
        """Internal wrapper to handle dependency waiting and execution."""
        try:
            # 1. Wait for dependencies
            if node.depends_on:
                logger.debug(f"Node {name} waiting for {node.depends_on}")
                # Wait for all dependency futures to complete
                await asyncio.gather(*(self.futures[dep] for dep in node.depends_on))
                
                # Check if any dependency failed or was cancelled
                for dep in node.depends_on:
                    dep_res = self.results.get(dep)
                    if not dep_res or dep_res.error or dep_res.cancelled:
                        logger.warning(f"Node {name} skipped because dependency {dep} failed/missing")
                        self._mark_cancelled(name)
                        return

            # 2. Check cancellation (e.g. if luxury and system overloaded)
            # (TODO: integrate dynamic cancellation check here)
            
            # 3. Execute
            logger.debug(f"Node {name} starting...")
            t0 = time.time()
            
            # Resolve args (some might be outputs from dependencies)
            # NOTE: For this v1, we assume args are passed fully formed or are global state.
            # To make it truly powerful, we need dependency injection of results.
            # Implemented simple injection: checks if arg is a dependency name
            resolved_args = []
            for arg in node.args:
                if isinstance(arg, str) and arg in self.results:
                    resolved_args.append(self.results[arg].result)
                else:
                    resolved_args.append(arg)
            
            # Run the function
            result_val = await node.func(*resolved_args, **node.kwargs)
            duration = time.time() - t0
            
            # 4. Store Result
            self.results[name] = NodeResult(name, result_val, duration)
            self.futures[name].set_result(True) # Signal downstream
            logger.debug(f"Node {name} finished in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Node {name} crashed: {e}", exc_info=True)
            self.results[name] = NodeResult(name, None, 0, error=e)
            # Unblock downstream but they will see the error
            self.futures[name].set_result(False)

    def _mark_cancelled(self, name: str):
        self.results[name] = NodeResult(name, None, 0, cancelled=True)
        self.futures[name].set_result(False)
        
    def cancel_all(self):
        """Emergency stop"""
        for task in self._running_tasks:
            task.cancel()
