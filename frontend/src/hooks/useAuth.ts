import { useCallback, useEffect, useState } from "react";

import { supabase } from "@/lib/supabase";
import type { AuthState } from "@/types";

/**
 * Reactive Supabase auth state.
 *
 * Subscribes to `onAuthStateChange` on mount and cleans up on
 * unmount. Provides the current user, session, loading flag,
 * and sign-out helper.
 */
export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    loading: true,
  });

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setState({
        user: session?.user ?? null,
        session,
        loading: false,
      });
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({
        user: session?.user ?? null,
        session,
        loading: false,
      });
    });

    return () => subscription.unsubscribe();
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  return { ...state, signOut };
}
