import apiClient from "./client";

export async function createDonation(payload) {
  const { data } = await apiClient.post("/donations", payload);
  return data;
}

export async function getMyDonations(params = {}) {
  const { data } = await apiClient.get("/donations/mine", { params });
  return data;
}

export async function updateDonation(donationId, payload) {
  const { data } = await apiClient.put(`/donations/${donationId}`, payload);
  return data;
}

export async function cancelDonation(donationId) {
  const { data } = await apiClient.post(`/donations/${donationId}/cancel`);
  return data;
}
