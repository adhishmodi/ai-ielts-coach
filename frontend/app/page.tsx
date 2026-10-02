"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(localStorage.getItem("access_token") ? "/writing" : "/login");
  }, [router]);

  return <main className="center-page"><div className="loader">Loading AI IELTS Coach…</div></main>;
}