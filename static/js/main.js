/**
 * Campus Lost & Found Portal - Frontend Utilities & Interactions
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Initialize Lucide Icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // 2. Mobile Navigation Toggle
  const navToggleBtn = document.getElementById("navToggleBtn");
  const mobileMenu = document.getElementById("navbarMobileMenu");
  if (navToggleBtn && mobileMenu) {
    navToggleBtn.addEventListener("click", () => {
      mobileMenu.classList.toggle("open");
    });
  }

  // 3. Dismissible Flash Alerts
  document.querySelectorAll(".alert-close").forEach((button) => {
    button.addEventListener("click", (e) => {
      const alertBox = e.target.closest(".alert");
      if (alertBox) {
        alertBox.style.opacity = "0";
        alertBox.style.transform = "translateY(-8px)";
        alertBox.style.transition = "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)";
        setTimeout(() => alertBox.remove(), 200);
      }
    });
  });

  // 4. Tab Navigation (Dashboard & Detailed views)
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-tab");
      const parentContainer = btn.closest(".tabs-wrapper") || document;

      // Update button state
      parentContainer.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Update tab pane state
      parentContainer.querySelectorAll(".tab-pane").forEach((pane) => {
        pane.classList.remove("active");
        if (pane.id === targetId) {
          pane.classList.add("active");
        }
      });

      // Re-hydrate icons if new elements become visible
      if (window.lucide) {
        window.lucide.createIcons();
      }
    });
  });

  // 5. Image Upload Live Preview & Drag-and-Drop
  const imageInput = document.getElementById("image");
  const imagePreviewContainer = document.getElementById("imagePreviewContainer");
  const imagePreviewImg = document.getElementById("imagePreviewImg");
  const dropzone = document.querySelector(".file-upload-dropzone");

  function handleImageFile(file) {
    if (!file) {
      if (imagePreviewContainer) imagePreviewContainer.style.display = "none";
      return;
    }

    // Client-side validation: < 5MB
    if (file.size > 5 * 1024 * 1024) {
      alert("Selected image exceeds 5MB. Please choose a smaller image file.");
      if (imageInput) imageInput.value = "";
      if (imagePreviewContainer) imagePreviewContainer.style.display = "none";
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      if (imagePreviewImg) {
        imagePreviewImg.src = event.target.result;
      }
      if (imagePreviewContainer) {
        imagePreviewContainer.style.display = "flex";
      }
    };
    reader.readAsDataURL(file);
  }

  if (imageInput) {
    imageInput.addEventListener("change", (e) => {
      handleImageFile(e.target.files[0]);
    });
  }

  if (dropzone && imageInput) {
    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.style.borderColor = "var(--primary)";
        dropzone.style.backgroundColor = "var(--primary-light)";
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.style.borderColor = "";
        dropzone.style.backgroundColor = "";
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        imageInput.files = files;
        handleImageFile(files[0]);
      }
    });
  }

  // 6. Generic Confirmation for Destructive Actions
  document.querySelectorAll("[data-confirm]").forEach((element) => {
    element.addEventListener("click", (e) => {
      const message = element.getAttribute("data-confirm") || "Are you sure you want to proceed?";
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // 7. Global Keyboard Shortcut: '/' focuses search input
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      const searchInput = document.querySelector(".search-bar-input") || document.getElementById("q");
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    }
  });

  // 8. Graceful image fallback - ensures no broken image icons ever appear
  window.addEventListener(
    "error",
    (e) => {
      const target = e.target;
      if (target && target.tagName === "IMG" && !target.dataset.fallbackAttempted) {
        target.dataset.fallbackAttempted = "true";
        target.classList.add("is-placeholder");
        target.src = "/static/images/placeholder.svg";
      }
    },
    true
  );
});
