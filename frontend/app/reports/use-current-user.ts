'use client';

import { useEffect, useState } from 'react';

import {
  getCurrentUser,
  type CurrentUser,
} from '@/lib/auth';

export function useCurrentUser() {
  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);

  useEffect(() => {
    setCurrentUser(getCurrentUser());
  }, []);

  return currentUser;
}
