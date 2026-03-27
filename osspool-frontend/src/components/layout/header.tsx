"use client";

import Link from "next/link";
import { useEffect, useState, useMemo } from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import type { User } from "@supabase/supabase-js";

export function Header() {
  const [user, setUser] = useState<User | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setAuthError(null);
    });
    return () => subscription.unsubscribe();
  }, [supabase]);

  const handleSignIn = async () => {
    setAuthError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: `${window.location.origin}/api/auth/callback` },
    });
    if (error) {
      setAuthError(error.message);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">OG</span>
            </div>
            <span className="font-bold text-xl">
              Open<span className="text-primary">Get</span>
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm">
            <Link
              href="/repos"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Repos
            </Link>
            <Link
              href="/contributors"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Contributors
            </Link>
            <Link
              href="/donate"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Donate
            </Link>
            {user && (
              <>
                <Link
                  href="/list-repo"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  List a Repo
                </Link>
                <Link
                  href="/dashboard"
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Dashboard
                </Link>
              </>
            )}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          {authError && (
            <span className="text-xs text-amber-500 max-w-[200px] text-right hidden sm:inline">
              {authError}
            </span>
          )}
          {user ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground hidden sm:inline">
                {user.user_metadata?.user_name || user.email}
              </span>
              {user.user_metadata?.avatar_url && (
                <img
                  src={user.user_metadata.avatar_url}
                  alt="Avatar"
                  className="h-8 w-8 rounded-full"
                />
              )}
              <Button variant="ghost" size="sm" onClick={handleSignOut}>
                Sign out
              </Button>
            </div>
          ) : (
            <Button onClick={handleSignIn} size="sm">
              Sign in with GitHub
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
