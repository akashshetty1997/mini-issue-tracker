import { http } from "@/lib/api/client";
import { API_V1_PREFIX } from "@/lib/constants";
import type { Meta, User } from "@/lib/types";

export const referenceApi = {
  users: (signal?: AbortSignal) => http.get<User[]>(`${API_V1_PREFIX}/users`, undefined, signal),
  meta: (signal?: AbortSignal) => http.get<Meta>(`${API_V1_PREFIX}/meta`, undefined, signal),
};
