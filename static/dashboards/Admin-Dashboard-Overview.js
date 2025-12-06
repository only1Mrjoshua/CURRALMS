  // Mobile Sidebar Toggle Functionality
  const sidebar = document.getElementById('sidebar');
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const hamburgerMenu = document.getElementById('hamburgerMenu');
  const overlay = document.getElementById('overlay');
  
  function toggleSidebar() {
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
    document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
  }
  
  mobileMenuBtn.addEventListener('click', toggleSidebar);
  hamburgerMenu.addEventListener('click', toggleSidebar);
  overlay.addEventListener('click', toggleSidebar);

  // Theme Management
  const themeToggle = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeIcon');
  const htmlElement = document.documentElement;

  // Function to set theme
  function setTheme(theme) {
    htmlElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    // Update icon
    if (theme === 'dark') {
      themeIcon.className = 'fas fa-sun';
    } else {
      themeIcon.className = 'fas fa-moon';
    }
  }

  // Function to toggle theme
  function toggleTheme() {
    const currentTheme = htmlElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
  }

  // Initialize theme
  function initTheme() {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(prefersDark ? 'dark' : 'light');
    }
  }

  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    // Only change if user hasn't set a preference
    if (!localStorage.getItem('theme')) {
      setTheme(e.matches ? 'dark' : 'light');
    }
  });

  // ⚙️ API Configuration - UPDATED FOR BEARER TOKEN AUTH
  const getApiBaseUrl = () => {
    // Check if we're on Render production
    if (window.location.hostname.includes("onrender.com")) {
      return "https://curralms-backend.onrender.com";
    }
    // Local development
    return "http://localhost:8000";
  };

  const API_BASE_URL = getApiBaseUrl();

  // Environment detection
  function getEnvironment() {
    return window.location.hostname.includes("onrender.com")
      ? "production"
      : "development";
  }

  // URL helper functions for frontend navigation
  function getBasePath() {
    if (getEnvironment() === "development") {
      return "/static";
    }
    return "";
  }

  function getUrl(path) {
    const basePath = getBasePath();
    return `${basePath}${path}`;
  }

  // Enhanced fetch wrapper with Bearer Token headers - FIXED
  async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    // Get token from localStorage for Authorization header
    const token = localStorage.getItem('access_token');
    
    const config = {
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        ...options.headers,
      },
      ...options,
    };

    // Add Authorization header if token exists
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }

    console.log(`📡 API Call: ${url}`, {
      method: config.method,
      hasToken: !!token,
      environment: getEnvironment(),
    });

    try {
      const response = await fetch(url, config);

      console.log(`📨 Response: ${response.status} ${response.statusText}`, {
        url: url,
        status: response.status,
        ok: response.ok,
      });

      // Handle 401 Unauthorized - redirect to login
      if (response.status === 401) {
        console.log("🔐 Token expired or invalid, redirecting to login");
        clearAuthData();
        showToast(
          "warning",
          "Session Expired",
          "Please log in again",
          3000
        );
        setTimeout(() => {
          window.location.href = getUrl("/signin.html");
        }, 2000);
        throw new Error("Authentication required");
      }

      // Handle 404 Not Found - return empty array instead of error
      if (response.status === 404) {
        console.log(`⚠️ Endpoint not found: ${url}, returning empty data`);
        return { ok: true, json: async () => [] };
      }

      return response;
    } catch (error) {
      console.error(`❌ API Call Failed: ${url}`, error);
      // Return a mock response for offline/error scenarios
      return {
        ok: false,
        status: 500,
        json: async () => ({ error: "Network error" })
      };
    }
  }

  // Token and Auth Management - UPDATED FOR BEARER TOKENS
  function clearAuthData() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
    localStorage.removeItem('token_expires_in');
    localStorage.removeItem('user');
    localStorage.removeItem('auth_error');
    localStorage.removeItem('success_message');
    localStorage.removeItem('dashboard_previous_data');
    console.log("🧹 Auth data cleared from localStorage");
  }

  // FIXED: Check if token is expired - SIMPLIFIED VERSION
  function isTokenExpired() {
    const token = localStorage.getItem('access_token');
    if (!token) return true;
    
    try {
      // Simple check - if we have a token, assume it's valid for now
      // The backend will return 401 if it's actually expired
      console.log("🔐 Token exists, validity will be checked by backend");
      return false;
    } catch (error) {
      console.error("Error checking token:", error);
      return true;
    }
  }

  // FIXED: Function to check if user is authenticated
  function checkAuthentication() {
    const token = localStorage.getItem("access_token");
    
    if (!token) {
      console.log("❌ No access token found");
      showToast(
        "warning",
        "Authentication Required",
        "Please log in to access the dashboard",
        3000
      );
      setTimeout(() => {
        window.location.href = getUrl("/signin.html");
      }, 2000);
      return false;
    }
    
    // Don't do aggressive expiration checking here
    // Let the backend handle token validation
    console.log("✅ Token found, proceeding with API calls");
    return true;
  }

  // Logout Confirmation Elements
  const logoutBtn = document.getElementById("logoutBtn");
  const logoutConfirmationModal = document.getElementById("logoutConfirmationModal");
  const confirmYes = document.getElementById("confirmYes");
  const confirmNo = document.getElementById("confirmNo");

  // Function to load and display current user info
  function loadCurrentUserInfo() {
    const userData = localStorage.getItem('user');
    if (userData) {
      try {
        const user = JSON.parse(userData);
        
        // Update the UI with user's information
        const userNameElement = document.getElementById("currentUserName");
        const userAvatarElement = document.getElementById("currentUserAvatar");

        if (userNameElement) {
          userNameElement.textContent = user.full_name || user.username || user.email || "User";
        }

        if (userAvatarElement) {
          userAvatarElement.textContent = getInitials(user.full_name || user.username || user.email);
        }

        console.log("👤 User info loaded:", user.username || user.email);
      } catch (e) {
        console.error("Error parsing user data:", e);
        setDefaultUserInfo();
      }
    } else {
      setDefaultUserInfo();
    }
  }

  function setDefaultUserInfo() {
    const userNameElement = document.getElementById("currentUserName");
    const userAvatarElement = document.getElementById("currentUserAvatar");

    if (userNameElement) {
      userNameElement.textContent = "User";
    }

    if (userAvatarElement) {
      userAvatarElement.textContent = "U";
    }
  }

  // Helper function to get initials from email or name
  function getInitials(text) {
    if (!text) return "?";

    // If it's an email, use the part before @
    if (text.includes("@")) {
      const username = text.split("@")[0];
      return username.charAt(0).toUpperCase();
    }

    // If it's a name, use the first character
    return text.charAt(0).toUpperCase();
  }

  // Function to fetch data from API with proper authentication
  async function fetchData(endpoint) {
    try {
      console.log(`🔍 Fetching from: ${API_BASE_URL}${endpoint}`);

      const response = await apiFetch(endpoint, {
        method: "GET",
      });

      console.log(`📊 Response status: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        console.warn(`⚠️ HTTP warning! status: ${response.status} for ${endpoint}`);
        // Return empty array for non-200 responses instead of throwing error
        return [];
      }

      const data = await response.json();
      console.log(`✅ Fetched data from ${endpoint}:`, data);
      return data;
    } catch (error) {
      console.error(`❌ Error fetching data from ${endpoint}:`, error);
      return [];
    }
  }

  // Function to fetch all assignments
  async function fetchAllAssignments() {
    try {
      console.log("📝 Fetching all assignments for total count...");
      
      // Use the exact endpoint from your backend
      const assignments = await fetchData("/assignments/");
      
      console.log(`📝 Total assignments found: ${assignments?.length || 0}`);
      return assignments || [];
    } catch (error) {
      console.error("❌ Error fetching all assignments:", error);
      return [];
    }
  }

  // Function to fetch all courses (for total count)
  async function fetchAllCourses() {
    try {
      console.log("📚 Fetching all courses for total count...");
      
      // First try to get all courses directly
      let allCourses = await fetchData("/courses/");
      
      // If that fails or returns empty, fetch by each category and combine
      if (!allCourses || allCourses.length === 0) {
        console.log("🔄 Falling back to category-based course fetching...");
        const categories = ["design", "development", "blockchain", "cyber security"];
        const categoryPromises = categories.map(category => 
          fetchData(`/courses/by-category/${category}`)
        );
        
        const categoryResults = await Promise.all(categoryPromises);
        allCourses = categoryResults.flat();
      }
      
      console.log(`📚 Total courses found: ${allCourses.length}`);
      return allCourses;
    } catch (error) {
      console.error("❌ Error fetching all courses:", error);
      return [];
    }
  }

  // Function to fetch all lessons (for total count)
  async function fetchAllLessons() {
    try {
      console.log("📖 Fetching all lessons for total count...");
      
      // Try to get all lessons directly
      let allLessons = await fetchData("/lessons/");
      
      // Fallback to category-based fetching
      if (!allLessons || allLessons.length === 0) {
        console.log("🔄 Falling back to category-based lesson fetching...");
        const categories = ["design", "development", "blockchain", "cyber security"];
        const categoryPromises = categories.map(category => 
          fetchData(`/lessons/category/${category}`)
        );
        
        const categoryResults = await Promise.all(categoryPromises);
        allLessons = categoryResults.flat();
      }
      
      console.log(`📖 Total lessons found: ${allLessons.length}`);
      return allLessons;
    } catch (error) {
      console.error("❌ Error fetching all lessons:", error);
      return [];
    }
  }

  // Function to fetch all quizzes (for total count)
  async function fetchAllQuizzes() {
    try {
      console.log("🧪 Fetching all quizzes for total count...");
      
      // Try to get all quizzes directly
      let allQuizzes = await fetchData("/quizzes/");
      
      // Fallback to category-based fetching
      if (!allQuizzes || allQuizzes.length === 0) {
        console.log("🔄 Falling back to category-based quiz fetching...");
        const categories = ["design", "development", "blockchain", "cyber security"];
        const categoryPromises = categories.map(category => 
          fetchData(`/quizzes/category/${category}`)
        );
        
        const categoryResults = await Promise.all(categoryPromises);
        allQuizzes = categoryResults.flat();
      }
      
      console.log(`🧪 Total quizzes found: ${allQuizzes.length}`);
      return allQuizzes;
    } catch (error) {
      console.error("❌ Error fetching all quizzes:", error);
      return [];
    }
  }

  // Function to fetch user statistics
  async function fetchUserStats() {
    try {
      console.log("👥 Fetching user statistics...");
      
      // Try different possible endpoints for user data
      const endpoints = [
        "/users/admin/users-status",
        "/users/active",
        "/users/"
      ];
      
      for (const endpoint of endpoints) {
        try {
          const userData = await fetchData(endpoint);
          if (userData && (Array.isArray(userData) || userData.count !== undefined)) {
            console.log(`✅ User data found from ${endpoint}:`, userData);
            return userData;
          }
        } catch (error) {
          console.log(`⚠️ Endpoint ${endpoint} failed, trying next...`);
        }
      }
      
      // If all endpoints fail, return default structure
      console.log("⚠️ No user endpoints worked, using default data");
      return { active: 0, inactive: 0, total: 0 };
    } catch (error) {
      console.error("❌ Error fetching user stats:", error);
      return { active: 0, inactive: 0, total: 0 };
    }
  }

  // Function to calculate percentage change
  function calculatePercentageChange(current, previous) {
    if (!previous || previous === 0) return current > 0 ? 100 : 0;
    return Math.round(((current - previous) / previous) * 100);
  }

  // Function to format date
  function formatDate(date) {
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  // Helper function to normalize category names for API calls
  function normalizeCategoryForAPI(category) {
    const normalized = category.toLowerCase().trim();

    console.log(`🔄 Normalizing category: "${category}" -> "${normalized}"`);

    // Map to API-friendly category names based on your database categories
    if (normalized.includes("cyber") || normalized.includes("security")) {
      return "cyber%20security"; // URL encoded for API call
    }
    if (normalized.includes("design")) {
      return "design";
    }
    if (normalized.includes("blockchain")) {
      return "blockchain";
    }
    if (normalized.includes("dev") || normalized.includes("programming") || normalized.includes("code")) {
      return "development";
    }

    return normalized;
  }

  // Function to fetch courses by category
  async function fetchCoursesByCategory(category) {
    try {
      const apiCategory = normalizeCategoryForAPI(category);
      console.log(`📚 Fetching courses for category: "${category}" -> API: "${apiCategory}"`);
      const courses = await fetchData(`/courses/by-category/${apiCategory}`);
      console.log(`📚 Found ${courses?.length || 0} courses for ${category}`);
      return courses || [];
    } catch (error) {
      console.error(`Error fetching courses for category ${category}:`, error);
      return [];
    }
  }

  // Function to fetch lessons by category
  async function fetchLessonsByCategory(category) {
    try {
      const apiCategory = normalizeCategoryForAPI(category);
      console.log(`📖 Fetching lessons for category: "${category}" -> API: "${apiCategory}"`);
      const lessons = await fetchData(`/lessons/category/${apiCategory}`);
      console.log(`📖 Found ${lessons?.length || 0} lessons for ${category}`);
      return lessons || [];
    } catch (error) {
      console.error(`Error fetching lessons for category ${category}:`, error);
      return [];
    }
  }

  // Function to fetch quizzes by category
  async function fetchQuizzesByCategory(category) {
    try {
      const apiCategory = normalizeCategoryForAPI(category);
      console.log(`🧪 Fetching quizzes for category: "${category}" -> API: "${apiCategory}"`);
      const quizzes = await fetchData(`/quizzes/category/${apiCategory}`);
      console.log(`🧪 Found ${quizzes?.length || 0} quizzes for ${category}`);
      return quizzes || [];
    } catch (error) {
      console.error(`Error fetching quizzes for category ${category}:`, error);
      return [];
    }
  }

  // Function to fetch assignments by category
  async function fetchAssignmentsByCategory(category) {
    try {
      const apiCategory = normalizeCategoryForAPI(category);
      console.log(`📝 Fetching assignments for category: "${category}" -> API: "${apiCategory}"`);
      
      // First get all assignments
      const allAssignments = await fetchAllAssignments();
      
      // Then filter by category
      const categoryAssignments = allAssignments.filter(assignment => {
        const assignmentCategory = assignment.category?.toLowerCase() || '';
        const normalizedCategory = category.toLowerCase();
        return assignmentCategory.includes(normalizedCategory) || 
               normalizedCategory.includes(assignmentCategory);
      });
      
      console.log(`📝 Found ${categoryAssignments?.length || 0} assignments for ${category}`);
      return categoryAssignments || [];
    } catch (error) {
      console.error(`Error fetching assignments for category ${category}:`, error);
      return [];
    }
  }

  // UPDATED: Function to update dashboard with all data
  async function updateDashboard() {
    console.log("🔄 Fetching dashboard data...");

    // Check authentication first - BUT DON'T REDIRECT IMMEDIATELY
    const token = localStorage.getItem("access_token");
    if (!token) {
      console.log("❌ No token found, showing warning but not redirecting immediately");
      showToast(
        "warning",
        "Authentication Required",
        "Please log in to view dashboard data",
        5000
      );
      // Don't redirect immediately, let user see the message
      return;
    }

    try {
      // Fetch all data in parallel using the new functions
      const [allCourses, allLessons, allQuizzes, allAssignments, userStats] = await Promise.all([
        fetchAllCourses(),
        fetchAllLessons(),
        fetchAllQuizzes(),
        fetchAllAssignments(),
        fetchUserStats(),
      ]);

      console.log("📦 All main data fetched:", {
        courses: allCourses?.length || 0,
        lessons: allLessons?.length || 0,
        quizzes: allQuizzes?.length || 0,
        assignments: allAssignments?.length || 0,
        userStats: userStats,
      });

      // Now fetch category-specific data
      const categories = ["Design", "Development", "Blockchain", "Cyber Security"];

      console.log("🎯 Fetching category-specific data...");

      // Fetch category data in parallel
      const categoryPromises = categories.map(async (category) => {
        const [categoryCourses, categoryLessons, categoryQuizzes, categoryAssignments] = await Promise.all([
          fetchCoursesByCategory(category),
          fetchLessonsByCategory(category),
          fetchQuizzesByCategory(category),
          fetchAssignmentsByCategory(category),
        ]);

        console.log(`📊 ${category}: ${categoryCourses.length} courses, ${categoryLessons.length} lessons, ${categoryQuizzes.length} quizzes, ${categoryAssignments.length} assignments`);

        return {
          category,
          courses: categoryCourses,
          lessons: categoryLessons,
          quizzes: categoryQuizzes,
          assignments: categoryAssignments,
        };
      });

      const categoryData = await Promise.all(categoryPromises);
      console.log("📊 Complete category data:", categoryData);

      // Process user statistics
      let activeUsers = 0;
      let inactiveUsers = 0;
      let totalUsers = 0;

      if (Array.isArray(userStats)) {
        // If userStats is an array of user objects
        activeUsers = userStats.filter(user => user.is_active === true).length;
        inactiveUsers = userStats.filter(user => user.is_active === false).length;
        totalUsers = userStats.length;
      } else if (userStats && typeof userStats === 'object') {
        // If userStats is an object with counts
        activeUsers = userStats.active || userStats.activeUsers || userStats.count || 0;
        inactiveUsers = userStats.inactive || userStats.inactiveUsers || 0;
        totalUsers = userStats.total || (activeUsers + inactiveUsers);
      } else {
        // Default fallback
        activeUsers = 0;
        inactiveUsers = 0;
        totalUsers = 0;
      }

      console.log(`👥 User statistics - Active: ${activeUsers}, Inactive: ${inactiveUsers}, Total: ${totalUsers}`);

      updateUIWithData(
        allCourses,
        allLessons,
        allQuizzes,
        allAssignments,
        { active: activeUsers, inactive: inactiveUsers, total: totalUsers },
        categoryData
      );
    } catch (error) {
      console.error("❌ Error in updateDashboard:", error);
      showToast(
        "error",
        "Data Fetch Error",
        "Could not load dashboard data. Please try again.",
        5000
      );
    }
  }

  // UPDATED: Function to update UI with actual data
  async function updateUIWithData(allCourses, allLessons, allQuizzes, allAssignments, userStats, categoryData) {
    console.log("🎨 Updating UI with data:", {
      courses: allCourses?.length,
      lessons: allLessons?.length,
      quizzes: allQuizzes?.length,
      assignments: allAssignments?.length,
      userStats: userStats,
      categoryData: categoryData?.length,
    });

    // Calculate basic statistics from database
    const totalCourses = allCourses ? allCourses.length : 0;
    const totalLessons = allLessons ? allLessons.length : 0;
    const totalQuizzes = allQuizzes ? allQuizzes.length : 0;
    const totalAssignments = allAssignments ? allAssignments.length : 0;

    // User statistics
    const activeUsers = userStats.active || 0;
    const inactiveUsers = userStats.inactive || 0;

    // Process category data for the UI
    const categoryStats = {
      Design: { courses: 0, lessons: 0, quizzes: 0, assignments: 0 },
      Development: { courses: 0, lessons: 0, quizzes: 0, assignments: 0 },
      Blockchain: { courses: 0, lessons: 0, quizzes: 0, assignments: 0 },
      "Cyber Security": { courses: 0, lessons: 0, quizzes: 0, assignments: 0 },
    };

    // Update category stats with fetched data
    if (categoryData) {
      categoryData.forEach(({ category, courses, lessons, quizzes, assignments }) => {
        if (categoryStats[category]) {
          categoryStats[category].courses = courses?.length || 0;
          categoryStats[category].lessons = lessons?.length || 0;
          categoryStats[category].quizzes = quizzes?.length || 0;
          categoryStats[category].assignments = assignments?.length || 0;
        }
      });
    }

    console.log("📈 Final category statistics:", categoryStats);

    // Get previous data from localStorage for comparison
    const previousData = JSON.parse(localStorage.getItem("dashboard_previous_data")) || {
      courses: 0,
      lessons: 0,
      assignments: 0,
      quizzes: 0,
      activeUsers: 0,
      inactiveUsers: 0,
      timestamp: new Date().toISOString(),
    };

    // Calculate percentages
    const coursesPercentage = calculatePercentageChange(totalCourses, previousData.courses);
    const lessonsPercentage = calculatePercentageChange(totalLessons, previousData.lessons);
    const assignmentsPercentage = calculatePercentageChange(totalAssignments, previousData.assignments);
    const quizzesPercentage = calculatePercentageChange(totalQuizzes, previousData.quizzes);
    const activeUsersPercentage = calculatePercentageChange(activeUsers, previousData.activeUsers);
    const inactiveUsersPercentage = calculatePercentageChange(inactiveUsers, previousData.inactiveUsers);

    // Update UI with real database data
    updateStatElement("total-courses", totalCourses);
    updateStatElement("total-lessons", totalLessons);
    updateStatElement("total-assignments", totalAssignments);
    updateStatElement("total-quizzes", totalQuizzes);
    updateStatElement("active-users", activeUsers);
    updateStatElement("inactive-users", inactiveUsers);

    // Update percentages
    updatePercentageElement("courses-percentage", coursesPercentage);
    updatePercentageElement("lessons-percentage", lessonsPercentage);
    updatePercentageElement("assignments-percentage", assignmentsPercentage);
    updatePercentageElement("quizzes-percentage", quizzesPercentage);
    updatePercentageElement("users-percentage", activeUsersPercentage);
    updatePercentageElement("inactive-percentage", inactiveUsersPercentage);

    // Update category statistics
    updateStatElement("design-courses", categoryStats["Design"].courses);
    updateStatElement("design-lessons", categoryStats["Design"].lessons);
    updateStatElement("design-quizzes", categoryStats["Design"].quizzes);

    updateStatElement("development-courses", categoryStats["Development"].courses);
    updateStatElement("development-lessons", categoryStats["Development"].lessons);
    updateStatElement("development-quizzes", categoryStats["Development"].quizzes);

    updateStatElement("blockchain-courses", categoryStats["Blockchain"].courses);
    updateStatElement("blockchain-lessons", categoryStats["Blockchain"].lessons);
    updateStatElement("blockchain-quizzes", categoryStats["Blockchain"].quizzes);

    updateStatElement("cybersecurity-courses", categoryStats["Cyber Security"].courses);
    updateStatElement("cybersecurity-lessons", categoryStats["Cyber Security"].lessons);
    updateStatElement("cybersecurity-quizzes", categoryStats["Cyber Security"].quizzes);

    // Store current data for next comparison
    localStorage.setItem(
      "dashboard_previous_data",
      JSON.stringify({
        courses: totalCourses,
        lessons: totalLessons,
        assignments: totalAssignments,
        quizzes: totalQuizzes,
        activeUsers: activeUsers,
        inactiveUsers: inactiveUsers,
        timestamp: new Date().toISOString(),
      })
    );

    // Update timestamps
    const now = new Date();
    const formattedDate = formatDate(now);
    document.querySelectorAll("#courses-updated, #lessons-updated, #assignments-updated, #quizzes-updated, #users-updated, #inactive-updated").forEach((el) => {
      el.textContent = formattedDate;
    });

    console.log("✅ Dashboard updated with database data");
    console.log("📊 Final counts from database:", {
      courses: totalCourses,
      lessons: totalLessons,
      assignments: totalAssignments,
      quizzes: totalQuizzes,
      activeUsers: activeUsers,
      inactiveUsers: inactiveUsers,
    });
  }

  // Helper function to update stat elements and remove loading state
  function updateStatElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
      element.innerHTML = "";
      element.textContent = value;
      element.classList.remove("skeleton-loading");
    }
  }

  // Helper function to update percentage elements with proper formatting
  function updatePercentageElement(elementId, percentage) {
    const element = document.getElementById(elementId);
    if (element) {
      element.innerHTML = "";
      
      const percentageElement = document.createElement('span');
      percentageElement.textContent = `${percentage}%`;
      
      // Add color based on positive/negative
      if (percentage > 0) {
        percentageElement.style.color = 'var(--success-green)';
      } else if (percentage < 0) {
        percentageElement.style.color = 'var(--error-red)';
      } else {
        percentageElement.style.color = 'var(--text-muted)';
      }
      
      element.appendChild(percentageElement);
      element.classList.remove("skeleton-loading");
    }
  }

  // Toast Notification System
  function showToast(type, title, message, duration = 5000) {
    let toastContainer = document.getElementById("toastContainer");
    if (!toastContainer) {
      toastContainer = document.createElement("div");
      toastContainer.id = "toastContainer";
      toastContainer.className = "toast-container";
      document.body.appendChild(toastContainer);
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    // Set border color based on type
    const colors = {
      success: "var(--success-green)",
      info: "var(--primary-indigo)",
      warning: "var(--accent-purple)",
      error: "var(--error-red)",
    };

    const icons = {
      success: "fas fa-check",
      info: "fas fa-info-circle",
      warning: "fas fa-exclamation-triangle",
      error: "fas fa-exclamation-circle",
    };

    toast.innerHTML = `
      <div class="toast-icon" style="color: ${colors[type] || colors.info}">
        <i class="${icons[type]}"></i>
      </div>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close">
        <i class="fas fa-times"></i>
      </button>
    `;

    toastContainer.appendChild(toast);

    // Show toast with animation
    setTimeout(() => {
      toast.classList.add('show');
    }, 100);

    // Close button functionality
    const closeBtn = toast.querySelector(".toast-close");
    closeBtn.addEventListener("click", () => {
      hideToast(toast);
    });

    // Auto-hide after duration
    if (duration > 0) {
      setTimeout(() => {
        hideToast(toast);
      }, duration);
    }

    return toast;
  }

  function hideToast(toast) {
    toast.classList.remove('show');
    toast.classList.add('hide');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  // Setup logout confirmation functionality
  function setupLogoutConfirmation() {
    logoutBtn.addEventListener("click", function (e) {
      e.preventDefault();
      logoutConfirmationModal.style.display = "block";
    });

    confirmNo.addEventListener("click", function () {
      logoutConfirmationModal.style.display = "none";
    });

    confirmYes.addEventListener("click", function () {
      showToast(
        "info",
        "Logging Out",
        "You have been logged out successfully",
        500
      );

      // Clear authentication tokens using the updated function
      clearAuthData();

      setTimeout(() => {
        window.location.href = getUrl("/signin.html");
      }, 500);
    });

    // Close logout confirmation modal when clicking outside
    window.addEventListener("click", function (event) {
      if (event.target === logoutConfirmationModal) {
        logoutConfirmationModal.style.display = "none";
      }
    });
  }

  // FIXED: Initialize dashboard with better auth handling
  document.addEventListener("DOMContentLoaded", function () {
    console.log("Dashboard initializing...");

    // Initialize theme first
    initTheme();

    // Set up theme toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Load current user info first
    loadCurrentUserInfo();

    // Setup logout confirmation
    setupLogoutConfirmation();

    // Check if we have a token, but don't redirect immediately
    const token = localStorage.getItem("access_token");
    if (!token) {
      console.log("⚠️ No token found, showing warning");
      showToast(
        "warning",
        "Not Logged In",
        "Please log in to view dashboard data",
        5000
      );
    } else {
      console.log("✅ Token found, loading dashboard data");
      // Load data immediately if we have a token
      updateDashboard();
    }

    // Set up periodic refresh (every 2 minutes) - only if we have a token
    if (token) {
      setInterval(() => {
        console.log("Refreshing dashboard data...");
        updateDashboard();
      }, 120000);
    }

    // Add active class to clicked sidebar items
    const sidebarItems = document.querySelectorAll(".sidebar-menu a");
    sidebarItems.forEach((item) => {
      item.addEventListener("click", function () {
        sidebarItems.forEach((i) => i.classList.remove("active"));
        this.classList.add("active");
        
        // Close sidebar on mobile after clicking a link
        if (window.innerWidth <= 992) {
          toggleSidebar();
        }
      });
    });
  });