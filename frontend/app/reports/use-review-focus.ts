'use client';

import {
  type RefObject,
  useEffect,
  useRef,
  useState,
} from 'react';
import { type ReadonlyURLSearchParams } from 'next/navigation';

import { type Report } from '@/lib/report';

export function useReviewFocus({
  selected,
  searchParams,
}: {
  selected: Report | null;
  searchParams: ReadonlyURLSearchParams;
}): {
  reviewSectionRef: RefObject<HTMLDivElement | null>;
  highlightReviewSection: boolean;
  openReviewDetails: boolean;
} {
  const reviewSectionRef = useRef<HTMLDivElement | null>(null);
  const [highlightReviewSection, setHighlightReviewSection] = useState(false);
  const openReviewDetails = searchParams.get('focus') === 'review';

  useEffect(() => {
    if (!selected || !openReviewDetails) {
      return;
    }

    const timer = window.setTimeout(() => {
      reviewSectionRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
      setHighlightReviewSection(true);
    }, 120);

    const clearTimer = window.setTimeout(() => {
      setHighlightReviewSection(false);
    }, 2600);

    return () => {
      window.clearTimeout(timer);
      window.clearTimeout(clearTimer);
    };
  }, [selected, openReviewDetails]);

  return {
    reviewSectionRef,
    highlightReviewSection,
    openReviewDetails,
  };
}
