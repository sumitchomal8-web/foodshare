import apiClient from "./client";

export async function getMyProfile() {
  const { data } = await apiClient.get("/users/me");
  return data;
}

export async function updateMyProfile(payload) {
  const { data } = await apiClient.patch("/users/me", payload);
  return data;
}
