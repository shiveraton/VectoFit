import client from "../config/client";

export interface AnnotationQueueItem {
  id: number;
  name: string;
  exercise_type: string;
  review_total: number;
  annotated_by_me: number;
  pending_for_me: number;
}

export const annotationQueueService = {
  async list(): Promise<AnnotationQueueItem[]> {
    const response = await client.get<AnnotationQueueItem[]>(
      "/datasets/annotation-queue/",
    );
    return response.data;
  },
};
