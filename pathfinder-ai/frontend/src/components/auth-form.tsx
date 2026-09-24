"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Logo } from "@/components/brand";
import { PathLines } from "@/components/landing/effects";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/primitives";
import { ApiError, get, post } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<"form" | "demo" | null>(null);
  const [google, setGoogle] = useState(false);
  const demoTriggered = useRef(false);

  const after = async () => {
    qc.clear();
    const me = await get<{ onboarding_completed: boolean }>("/auth/me");
    const next = params.get("next");
    router.replace(next && next.startsWith("/") ? next : me.onboarding_completed ? "/app" : "/onboarding");
  };

  const demo = async () => {
    setLoading("demo");
    setError(null);
    try {
      await post("/auth/demo");
      await after();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't open the demo.");
      setLoading(null);
    }
  };

  useEffect(() => {
    get<{ google: boolean }>("/auth/providers").then((p) => setGoogle(p.google)).catch(() => {});
    if (params.get("demo") === "1" && !demoTriggered.current) {
      demoTriggered.current = true;
      demo();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading("form");
    setError(null);
    try {
      await post(mode === "login" ? "/auth/login" : "/auth/register", mode === "login" ? { email, password } : { email, password, name });
      await after();
    } catch (err) {
      if (err instanceof ApiError && err.code === "validation_error") {
        const f = (err.details?.fields as { field: string; message: string }[] | undefined)?.[0];
        setError(f?.field === "password" ? "Use at least 8 characters for your password." : f?.field === "email" ? "Enter a valid email address." : err.message);
      } else setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setLoading(null);
    }
  };

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1fr_1.05fr]">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Logo />
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-16">
          <h1 className="text-[34px] font-semibold tracking-[-0.03em]">{mode === "login" ? "Welcome back." : "Start with you."}</h1>
          <p className="mt-3 text-fg-2">
            {mode === "login" ? "Pick up where you left off on your path." : "Create an account to save your profile and roadmap."}
          </p>
          <form onSubmit={submit} className="mt-10 space-y-5" noValidate>
            {mode === "signup" && (
              <div>
                <Label htmlFor="name">Name</Label>
                <Input id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="How should we greet you?" />
              </div>
            )}
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={8}
                value={password} onChange={(e) => setPassword(e.target.value)} placeholder={mode === "signup" ? "At least 8 characters" : undefined} />
            </div>
            {error && <p role="alert" className="text-[14px] text-danger">{error}</p>}
            <Button type="submit" size="lg" className="w-full" loading={loading === "form"}>
              {mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>
          <div className="my-6 flex items-center gap-3 text-[12px] text-muted"><div className="h-px flex-1 bg-line" />or<div className="h-px flex-1 bg-line" /></div>
          <div className="space-y-2">
            {google && (
              <Button asChild variant="secondary" size="lg" className="w-full">
                <a href="/api/v1/auth/oauth/google/login">Continue with Google</a>
              </Button>
            )}
            <Button variant="secondary" size="lg" className="w-full" onClick={demo} loading={loading === "demo"}>
              Explore with the demo profile
            </Button>
          </div>
          <p className="mt-8 text-[14px] text-fg-2">
            {mode === "login" ? "New here? " : "Already have an account? "}
            <Link href={mode === "login" ? "/signup" : "/login"} className="font-medium text-fg underline-offset-4 hover:underline">
              {mode === "login" ? "Create an account" : "Sign in"}
            </Link>
          </p>
        </div>
      </div>
      <aside className="relative hidden overflow-hidden border-l border-line bg-surface lg:block">
        <PathLines />
        <div className="absolute bottom-12 left-12 right-12">
          <p className="eyebrow mb-4">PathFinder AI</p>
          <p className="max-w-md text-[26px] font-semibold leading-tight tracking-[-0.025em]">
            Several paths, clearly explained. <span className="text-muted">You choose the one worth walking.</span>
          </p>
        </div>
      </aside>
    </div>
  );
}
