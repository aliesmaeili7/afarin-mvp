"use client";

import { EducationPostPage } from "./EducationPostPage";

export function EducationPostView({ postId }: { postId: string }) {
  return <EducationPostPage postId={postId} />;
}
