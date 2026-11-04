const sidebar = document.getElementById("appSidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const sidebarBackdrop = document.getElementById("sidebarBackdrop");

function closeSidebar() {
  if (!sidebar || !sidebarToggle) return;
  sidebar.classList.remove("is-open");
  sidebarBackdrop.classList.remove("is-visible");
  sidebarToggle.setAttribute("aria-expanded", "false");
  document.body.classList.remove("sidebar-open");
}

if (sidebar && sidebarToggle && sidebarBackdrop) {
  sidebarToggle.addEventListener("click", () => {
    const isOpen = sidebar.classList.toggle("is-open");
    sidebarBackdrop.classList.toggle("is-visible", isOpen);
    sidebarToggle.setAttribute("aria-expanded", String(isOpen));
    document.body.classList.toggle("sidebar-open", isOpen);
  });
  sidebarBackdrop.addEventListener("click", closeSidebar);
  sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeSidebar));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSidebar();
  });
}
