# Story: Authentication Flow & Route Protection

**Story ID**: EPIC-001-STORY-003  
**Epic**: Epic 1 - Authentication & Core Layout  
**Priority**: High  
**Estimated Effort**: 1-2 days  
**Dependencies**: EPIC-001-STORY-001, EPIC-001-STORY-002  
**Status**: Ready for Development

---

## User Story

**As a** user,  
**I want** automatic redirection based on my authentication status,  
**So that** I'm always viewing the appropriate screen for my session state.

---

## Acceptance Criteria

### Functional Requirements

1. **Protected Route Wrapper**
   - Wraps routes requiring authentication (`/home`, `/chat`, `/upload`)
   - Checks if user is authenticated (token exists in localStorage)
   - If authenticated → renders requested route
   - If not authenticated → redirects to `/login`
   - Preserves intended destination (after login, redirect to original URL)

2. **Auto-redirect After Login**
   - After successful login → redirect to `/home` (or preserved destination)
   - After successful registration → redirect to `/login` with success message
   - If already authenticated, visiting `/login` → redirect to `/home`

3. **Session Persistence**
   - On app load, check localStorage for `authToken`
   - If token exists → set auth context, allow access to protected routes
   - If token missing → redirect to `/login` when accessing protected routes
   - Token persists across page refreshes

4. **Token Expiration Handling**
   - If API returns 401 (unauthorized) → logout user, redirect to `/login`
   - Show message: "Your session has expired. Please log in again."
   - Clear localStorage on token expiration

5. **Loading States**
   - Show loading spinner while checking authentication on app init
   - Don't flash login page if user is authenticated (wait for auth check)
   - Smooth transition between screens (fade animations)

### Integration Requirements

6. **React Router Integration**
   - Use `<Navigate>` for redirects (React Router v6)
   - Use `useLocation()` to preserve intended destination
   - Protected routes wrapped in `<ProtectedRoute>` component

7. **Auth Context Integration**
   - Read `isAuthenticated` from AuthContext
   - Call `logout()` on token expiration (401 responses)

### Quality Requirements

8. **User Experience**
   - No "flicker" between login and protected routes on page load
   - Clear feedback when redirected due to auth status
   - Transitions smooth (250-300ms fade)

9. **Security**
   - Never show protected content before authentication verified
   - Token checked on every protected route access
   - API 401 responses handled globally (axios interceptor or fetch wrapper)

---

## Technical Notes

### ProtectedRoute Component

```javascript
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  
  if (!isAuthenticated) {
    // Save intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  return children;
};
```

### Login Redirect Logic

```javascript
const Login = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useAuth();
  
  const from = location.state?.from?.pathname || '/home';
  
  const handleLogin = async (email, password) => {
    // ... login logic
    login(userData, token);
    navigate(from, { replace: true }); // Redirect to intended destination
  };
};
```

### Global 401 Handler

```javascript
// API interceptor for 401 responses
const apiClient = async (url, options) => {
  const response = await fetch(url, options);
  
  if (response.status === 401) {
    const { logout } = useAuth();
    logout();
    navigate('/login', { state: { message: 'Session expired. Please log in again.' }});
    throw new Error('Unauthorized');
  }
  
  return response;
};
```

---

## Definition of Done

- [x] ProtectedRoute component redirects unauthenticated users to `/login`
- [x] After login, user redirected to intended destination (or `/home` by default)
- [x] Session persists across page refreshes
- [x] Token expiration (401) triggers logout and redirect to `/login`
- [x] No "flicker" on page load (loading state shows while auth is checked)
- [x] Transitions smooth (fade animations)
- [x] Already authenticated users visiting `/login` redirect to `/home`
- [x] API 401 responses handled globally

---

## Dependencies

- EPIC-001-STORY-001 (Authentication Screens)
- EPIC-001-STORY-002 (Application Shell with AuthContext)

---

**Story Status**: ✅ Ready for Development
