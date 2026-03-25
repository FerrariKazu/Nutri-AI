import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, ChevronRight, ChevronLeft, Save, 
  ChefHat, Microwave, Leaf, Target,
  CheckCircle2
} from 'lucide-react';

const SKILL_LEVELS = [
  { id: 'beginner', label: 'Beginner', desc: 'New to cooking or specific techniques', icon: <Microwave size={20} /> },
  { id: 'intermediate', label: 'Intermediate', desc: 'Comfortable with basics and multiple steps', icon: <ChefHat size={20} /> },
  { id: 'expert', label: 'Expert/Pro', desc: 'Strong foundation in science and technique', icon: <Target size={20} /> }
];

const DIETARY_OPTIONS = [
  'Vegan', 'Vegetarian', 'Gluten-Free', 'Dairy-Free', 'Keto', 'Paleo', 'Nut-Free', 'Low-Carb'
];

const EQUIPMENT_OPTIONS = [
  'Air Fryer', 'Instant Pot', 'Sous Vide', 'Cast Iron', 'Dutch Oven', 'Stand Mixer', 'Blender', 'Food Processor', 'Kitchen Scale'
];

const GOALS = [
  { id: 'mechanisms', label: 'Food Science', desc: 'Understanding "Why" and molecular logic' },
  { id: 'practical', label: 'Efficient Cooking', desc: 'Tips and tricks for better results' },
  { id: 'nutrition', label: 'Metabolic Nutrition', desc: 'Optimizing for health and biology' },
  { id: 'creativity', label: 'Culinary Creativity', desc: 'Flavor pairing and innovation' }
];

const PreferencesModal = ({ isOpen, onClose, onSave, initialData }) => {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({
    skill_level: 'intermediate',
    dietary_constraints: [],
    equipment: [],
    primary_goal: 'mechanisms',
    ...initialData
  });

  const [isSaving, setIsSaving] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const totalSteps = 4;

  const handleToggleList = (field, item) => {
    setFormData(prev => {
      const list = prev[field] || [];
      if (list.includes(item)) {
        return { ...prev, [field]: list.filter(i => i !== item) };
      } else {
        return { ...prev, [field]: [...list, item] };
      }
    });
  };

  const handleSave = async () => {
    setIsSaving(true);
    await onSave(formData);
    setIsSaving(false);
    setShowSuccess(true);
    setTimeout(() => {
      setShowSuccess(false);
      onClose();
    }, 1500);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div 
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="relative w-full max-w-2xl bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-800">
          <div>
            <h2 className="text-xl font-semibold text-white">Personalize Nutri</h2>
            <p className="text-sm text-zinc-400">Tailoring the engine to your culinary profile</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-400">
            <X size={20} />
          </button>
        </div>

        {/* Success Overlay */}
        <AnimatePresence>
          {showSuccess && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-zinc-900/90"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', damping: 12 }}
                className="text-emerald-500 mb-4"
              >
                <CheckCircle2 size={64} />
              </motion.div>
              <h3 className="text-2xl font-bold text-white">Profile Updated</h3>
              <p className="text-zinc-400">Nutri has adjusted its reasoning logic.</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Progress Bar */}
        <div className="h-1 bg-zinc-800">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${((step + 1) / totalSteps) * 100}%` }}
            className="h-full bg-emerald-500"
          />
        </div>

        {/* Content */}
        <div className="p-8 min-h-[400px]">
          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div
                key="step0"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-lg font-medium text-white mb-2">What's your culinary skill level?</h3>
                  <p className="text-zinc-400 text-sm">This adjusts the complexity and depth of technical explanations.</p>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  {SKILL_LEVELS.map(level => (
                    <button
                      key={level.id}
                      onClick={() => setFormData({ ...formData, skill_level: level.id })}
                      className={`flex items-start p-4 rounded-xl border transition-all ${
                        formData.skill_level === level.id 
                          ? 'bg-emerald-500/10 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.1)]' 
                          : 'bg-zinc-800/50 border-zinc-800 hover:border-zinc-700'
                      }`}
                    >
                      <div className={`p-2 rounded-lg mr-4 ${
                        formData.skill_level === level.id ? 'text-emerald-500 bg-emerald-500/20' : 'text-zinc-400 bg-zinc-800'
                      }`}>
                        {level.icon}
                      </div>
                      <div className="text-left">
                        <div className={`font-medium ${formData.skill_level === level.id ? 'text-white' : 'text-zinc-300'}`}>{level.label}</div>
                        <div className="text-xs text-zinc-500">{level.desc}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-lg font-medium text-white mb-2">Any dietary constraints?</h3>
                  <p className="text-zinc-400 text-sm">Nutri will proactively screen recommendations against these protocols.</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {DIETARY_OPTIONS.map(opt => (
                    <button
                      key={opt}
                      onClick={() => handleToggleList('dietary_constraints', opt)}
                      className={`p-3 rounded-lg border text-sm transition-all ${
                        formData.dietary_constraints.includes(opt)
                          ? 'bg-emerald-500/10 border-emerald-500 text-emerald-400'
                          : 'bg-zinc-800/50 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-lg font-medium text-white mb-2">What equipment do you use?</h3>
                  <p className="text-zinc-400 text-sm">Nutri will prioritize techniques compatible with your kitchen tools.</p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  {EQUIPMENT_OPTIONS.map(opt => (
                    <button
                      key={opt}
                      onClick={() => handleToggleList('equipment', opt)}
                      className={`p-3 rounded-lg border transition-all ${
                        formData.equipment.includes(opt)
                          ? 'bg-emerald-500/10 border-emerald-500 text-emerald-400'
                          : 'bg-zinc-800/50 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="text-lg font-medium text-white mb-2">What's your primary goal?</h3>
                  <p className="text-zinc-400 text-sm">This guides Nutri's "interesting angle" and commentary style.</p>
                </div>
                <div className="grid grid-cols-1 gap-3">
                  {GOALS.map(goal => (
                    <button
                      key={goal.id}
                      onClick={() => setFormData({ ...formData, primary_goal: goal.id })}
                      className={`flex flex-col p-4 rounded-xl border text-left transition-all ${
                        formData.primary_goal === goal.id 
                          ? 'bg-emerald-500/10 border-emerald-500' 
                          : 'bg-zinc-800/50 border-zinc-800 hover:border-zinc-700'
                      }`}
                    >
                      <div className={`font-medium ${formData.primary_goal === goal.id ? 'text-white' : 'text-zinc-300'}`}>{goal.label}</div>
                      <div className="text-xs text-zinc-500">{goal.desc}</div>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-zinc-800 bg-zinc-900/50">
          <button 
            onClick={() => setStep(s => Math.max(0, s - 1))}
            disabled={step === 0}
            className={`flex items-center text-sm font-medium ${step === 0 ? 'text-zinc-600' : 'text-zinc-400 hover:text-white'}`}
          >
            <ChevronLeft size={16} className="mr-1" /> Back
          </button>
          
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500">Step {step + 1} of {totalSteps}</span>
            {step === totalSteps - 1 ? (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-6 py-2 rounded-xl text-sm font-medium transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)]"
              >
                {isSaving ? 'Synchronizing...' : (
                  <><Save size={16} className="mr-2" /> Finish Setup</>
                )}
              </button>
            ) : (
              <button
                onClick={() => setStep(s => Math.min(totalSteps - 1, s + 1))}
                className="flex items-center bg-zinc-100 hover:bg-white text-zinc-950 px-6 py-2 rounded-xl text-sm font-medium transition-all shadow-lg"
              >
                Next <ChevronRight size={16} className="ml-1" />
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default PreferencesModal;
