const API_BASE = "http://localhost:8000/api";

export const getPage = async (params) => {
  const response = await fetch(`${API_BASE}/page`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });
  
  if (!response.ok) {
    throw new Error("Failed to fetch page");
  }
  
  const data = await response.ok ? await response.json() : {};
  // Handle relative URLs from backend
  if (data.imageUrl && data.imageUrl.startsWith("/static")) {
    data.imageUrl = `http://localhost:8000${data.imageUrl}`;
  }
  return data;
};

export const uploadImage = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to upload image");
  }

  const data = await response.json();
  if (data.imageUrl && data.imageUrl.startsWith("/static")) {
    data.imageUrl = `http://localhost:8000${data.imageUrl}`;
  }
  return data;
};
