import { keepPreviousData, useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { ApiError, api } from "./client";
import type {
  Creator, Hero, Job, PublicConfig, Rankings, ReelCard, ReelDetail, ReelPage, Transparency,
} from "./types";

const notFoundIsNull = (error: unknown) => error instanceof ApiError && error.status === 404;

export function usePublicConfig() {
  return useQuery({ queryKey: ["config"], queryFn: () => api<PublicConfig>("/config/public"), staleTime: 5 * 60_000 });
}

export function useHero() {
  return useQuery({ queryKey: ["hero"], queryFn: () => api<Hero | null>("/hero"), refetchInterval: 60_000 });
}

export function useReels(filters: { topic?: string; q?: string }) {
  return useInfiniteQuery({
    queryKey: ["reels", filters],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams();
      if (filters.topic) params.set("topic", filters.topic);
      if (filters.q) params.set("q", filters.q);
      if (pageParam) params.set("before", pageParam);
      return api<ReelPage>(`/reels?${params}`);
    },
    initialPageParam: "",
    getNextPageParam: (last) => last.next_before ?? undefined,
    placeholderData: keepPreviousData,
  });
}

export function useTopics() {
  return useQuery({
    queryKey: ["topics"],
    queryFn: () => api<{ items: { topic: string; reels: number }[] }>("/topics"),
    staleTime: 60_000,
  });
}

export function useReel(reelId: string) {
  return useQuery({
    queryKey: ["reel", reelId],
    queryFn: () => api<ReelDetail>(`/reels/${encodeURIComponent(reelId)}`),
    retry: (count, error) => !notFoundIsNull(error) && count < 2,
  });
}

export function useCreators() {
  return useQuery({ queryKey: ["creators"], queryFn: () => api<{ items: Creator[]; min_sample: number }>("/creators") });
}

export function useCreator(handle: string) {
  return useQuery({
    queryKey: ["creator", handle],
    queryFn: () => api<{ creator: Creator; reels: ReelCard[] }>(`/creators/${encodeURIComponent(handle)}`),
    retry: (count, error) => !notFoundIsNull(error) && count < 2,
  });
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api<Job>(`/jobs/${encodeURIComponent(jobId)}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "failed" || status === "rejected" ? false : 2500;
    },
  });
}

export function useTransparency() {
  return useQuery({ queryKey: ["transparency"], queryFn: () => api<Transparency>("/transparency") });
}

export function useRankings() {
  return useQuery({ queryKey: ["sources"], queryFn: () => api<Rankings>("/sources"), staleTime: 5 * 60_000 });
}
