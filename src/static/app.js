document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const toggleRegisterButton = document.getElementById("toggle-register");
  const logoutButton = document.getElementById("logout-button");
  const passwordForm = document.getElementById("password-form");
  const authStatus = document.getElementById("auth-status");
  let currentAccount = null;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function updateAuthUI(account) {
    currentAccount = account;
    const signedIn = Boolean(account);
    authStatus.textContent = signedIn
      ? `Signed in as ${account.full_name} (${account.role})`
      : "Not signed in";
    loginForm.classList.toggle("hidden", signedIn);
    registerForm.classList.toggle("hidden", signedIn || !registerForm.classList.contains("expanded"));
    toggleRegisterButton.classList.toggle("hidden", signedIn);
    logoutButton.classList.toggle("hidden", !signedIn);
    passwordForm.classList.toggle("hidden", !signedIn);
    signupForm.querySelector("button").disabled = !signedIn;
  }

  async function loadCurrentUser() {
    const response = await fetch("/auth/me");
    updateAuthUI(response.ok ? await response.json() : null);
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) => `<li><span class="participant-email">${email}</span>${
                      currentAccount && currentAccount.email === email
                        ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" aria-label="Unregister from ${name}">Remove</button>`
                        : ""
                    }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("login-username").value,
        password: document.getElementById("login-password").value,
      }),
    });
    const result = await response.json();
    if (!response.ok) return showMessage(result.detail, "error");
    loginForm.reset();
    updateAuthUI(result);
    fetchActivities();
    showMessage("Logged in successfully", "success");
  });

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("register-username").value,
        full_name: document.getElementById("register-name").value,
        email: document.getElementById("register-email").value,
        password: document.getElementById("register-password").value,
        date_of_birth: document.getElementById("register-dob").value,
        role: document.getElementById("register-role").value,
      }),
    });
    const result = await response.json();
    if (!response.ok) return showMessage(result.detail, "error");
    registerForm.reset();
    registerForm.classList.remove("expanded");
    updateAuthUI(null);
    showMessage("Account created. Please log in.", "success");
  });

  toggleRegisterButton.addEventListener("click", () => {
    registerForm.classList.toggle("expanded");
    updateAuthUI(null);
    toggleRegisterButton.textContent = registerForm.classList.contains("expanded")
      ? "Cancel account creation"
      : "Create an account";
  });

  logoutButton.addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST" });
    updateAuthUI(null);
    fetchActivities();
    showMessage("Logged out", "success");
  });

  passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/auth/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: document.getElementById("current-password").value,
        new_password: document.getElementById("new-password").value,
      }),
    });
    const result = await response.json();
    showMessage(result.message || result.detail, response.ok ? "success" : "error");
    if (response.ok) passwordForm.reset();
  });

  // Initialize app
  updateAuthUI(null);
  loadCurrentUser();
  fetchActivities();
});
