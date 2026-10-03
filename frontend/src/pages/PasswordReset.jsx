import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { EyebrowTag } from '../components/common/index';

export default function PasswordReset() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [step,            setStep]            = useState('request');
  const [email,           setEmail]           = useState('');
  const [newPassword,     setNewPassword]     = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading,         setLoading]         = useState(false);
  const [error,           setError]           = useState('');
  const [message,         setMessage]         = useState('');

  React.useEffect(() => {
    const token = searchParams.get('token');
    if (token) setStep('reset');
  }, [searchParams]);

  const handleRequestReset = async (e) => {
    e.preventDefault();
    setError(''); setMessage(''); setLoading(true);
    try {
      const response = await api.post('/api/auth/password-reset/request', { email: email.trim() });
      setMessage(response.data.message); setEmail('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to send reset email');
    } finally { setLoading(false); }
  };

  const handleConfirmReset = async (e) => {
    e.preventDefault();
    setError(''); setMessage('');
    if (newPassword !== confirmPassword) { setError('Passwords do not match'); return; }
    if (newPassword.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    const token = searchParams.get('token');
    try {
      await api.post('/api/auth/password-reset/confirm', { token, new_password: newPassword });
      setStep('success');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to reset password');
    } finally { setLoading(false); }
  };

  const inputClass =
    "w-full rounded-2xl bg-white/[0.09] border border-white/[0.14] px-4 py-3 text-sm text-white " +
    "placeholder-white/40 outline-none transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] " +
    "focus:border-accent-violet/50 focus:bg-white/[0.08] focus:shadow-[0_0_0_3px_rgba(221,112,11,0.18)]";

  return (
    <div className="min-h-[100dvh] flex items-center justify-center px-4 bg-surface-0">
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] rounded-full bg-accent-violet/[0.06] blur-[120px]" />
      </div>

      <div className="relative w-full max-w-sm animate-fade-up">
        <div className="p-1.5 rounded-[2rem] bg-white/[0.04] border border-white/[0.16] shadow-glass-strong">
          <div className="rounded-[calc(2rem-0.375rem)] bg-surface-1 p-7 shadow-[inset_0_1px_1px_rgba(255,255,255,0.07)]">

            {/* Header */}
            <div className="mb-7 space-y-3">
              <EyebrowTag>RAG Lab</EyebrowTag>
              <h1 className="text-2xl font-extrabold text-white tracking-tight">
                {step === 'request' && 'Reset Password'}
                {step === 'reset' && 'New Password'}
                {step === 'success' && 'All Done'}
              </h1>
              <p className="text-sm text-white/65">
                {step === 'request' && 'Enter your email to receive a reset link.'}
                {step === 'reset' && 'Choose a strong new password.'}
                {step === 'success' && 'Your password was reset successfully.'}
              </p>
            </div>

            {/* Alerts */}
            {error && (
              <div className="mb-4 rounded-2xl bg-red-500/[0.08] border border-red-500/[0.15] px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}
            {message && (
              <div className="mb-4 rounded-2xl bg-accent-emerald/[0.08] border border-accent-emerald/[0.15] px-4 py-3 text-sm text-accent-emerald-light">
                {message}
              </div>
            )}

            {/* Request form */}
            {step === 'request' && (
              <form onSubmit={handleRequestReset} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-[11px] uppercase tracking-[0.1em] font-semibold text-white/60">
                    Email Address
                  </label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    required className={inputClass} placeholder="your.email@example.com" />
                </div>
                <button type="submit" disabled={loading}
                  className="group w-full flex items-center justify-center gap-2.5 rounded-full
                    bg-accent-violet text-white py-3 text-sm font-bold mt-1
                    shadow-[0_0_0_1px_rgba(221,112,11,0.4),0_4px_24px_rgba(221,112,11,0.35)]
                    hover:bg-accent-violet-light active:scale-[0.97] disabled:opacity-40
                    transition-all duration-600 ease-[cubic-bezier(0.32,0.72,0,1)]">
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                      Sending…
                    </span>
                  ) : "Send Reset Link"}
                </button>
              </form>
            )}

            {/* Reset form */}
            {step === 'reset' && (
              <form onSubmit={handleConfirmReset} className="space-y-4">
                {[
                  { label: "New Password", val: newPassword, set: setNewPassword, placeholder: "At least 8 characters" },
                  { label: "Confirm Password", val: confirmPassword, set: setConfirmPassword, placeholder: "Repeat your password" },
                ].map(({ label, val, set, placeholder }) => (
                  <div key={label} className="space-y-1.5">
                    <label className="block text-[11px] uppercase tracking-[0.1em] font-semibold text-white/60">
                      {label}
                    </label>
                    <input type="password" value={val} onChange={(e) => set(e.target.value)}
                      required minLength={8} className={inputClass} placeholder={placeholder} />
                  </div>
                ))}
                <button type="submit" disabled={loading}
                  className="group w-full flex items-center justify-center gap-2.5 rounded-full
                    bg-accent-violet text-white py-3 text-sm font-bold
                    shadow-[0_0_0_1px_rgba(221,112,11,0.4),0_4px_24px_rgba(221,112,11,0.35)]
                    hover:bg-accent-violet-light active:scale-[0.97] disabled:opacity-40
                    transition-all duration-600 ease-[cubic-bezier(0.32,0.72,0,1)]">
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                      Resetting…
                    </span>
                  ) : "Set New Password"}
                </button>
              </form>
            )}

            {/* Success state */}
            {step === 'success' && (
              <div className="text-center space-y-5">
                <div className="mx-auto w-14 h-14 rounded-2xl bg-accent-emerald/10 border border-accent-emerald/20 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    className="text-accent-emerald-light">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <p className="text-sm text-white/50">Your password has been reset successfully.</p>
                <button onClick={() => navigate('/login')}
                  className="w-full flex items-center justify-center gap-2.5 rounded-full
                    bg-accent-violet text-white py-3 text-sm font-bold
                    shadow-[0_0_0_1px_rgba(221,112,11,0.4),0_4px_24px_rgba(221,112,11,0.35)]
                    hover:bg-accent-violet-light active:scale-[0.97]
                    transition-all duration-600 ease-[cubic-bezier(0.32,0.72,0,1)]">
                  Go to Login
                </button>
              </div>
            )}

            {/* Back link */}
            <div className="mt-6 pt-5 border-t border-white/[0.06] text-center">
              <button onClick={() => navigate('/login')}
                className="text-[12px] font-medium text-white/60 hover:text-accent-violet-light transition-colors duration-300">
                ← Back to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
