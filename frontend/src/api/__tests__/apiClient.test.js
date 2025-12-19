/**
 * Test API client WITHOUT React
 * Pure JavaScript testing
 */

import { sendPrompt, streamPrompt, healthCheck } from '../apiClient.js';

// Test 1: Send prompt
async function testSendPrompt() {
    console.log('Testing sendPrompt...');

    try {
        const response = await sendPrompt('Make me cookies', 'simple');
        console.log('✅ sendPrompt works:', response.answer.slice(0, 100));
    } catch (error) {
        console.error('❌ sendPrompt failed:', error.message);
    }
}

// Test 2: Stream prompt
function testStreamPrompt() {
    console.log('\nTesting streamPrompt...');

    let tokenCount = 0;

    const abort = streamPrompt(
        'What is protein?',
        'simple',
        (token) => {
            tokenCount++;
            process.stdout.write(token); // Print tokens as they arrive
        },
        (fullResponse) => {
            console.log(`\n✅ Stream complete! Received ${tokenCount} tokens`);
        },
        (error) => {
            console.error('\n❌ Stream failed:', error.message);
        }
    );

    // Test abort after 2 seconds
    // setTimeout(() => {
    //   console.log('\nAborting stream...');
    //   abort();
    // }, 2000);
}

// Test 3: Health check
async function testHealthCheck() {
    console.log('\nTesting healthCheck...');

    const isHealthy = await healthCheck();
    console.log(isHealthy ? '✅ Backend is healthy' : '❌ Backend is down');
}

// Run tests
(async () => {
    await testHealthCheck();
    await testSendPrompt();
    testStreamPrompt();
})();
