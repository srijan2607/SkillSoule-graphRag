# Story: Authentication Screens (Login & Registration)

**Story ID**: EPIC-001-STORY-001  
**Epic**: Epic 1 - Authentication & Core Layout  
**Priority**: High  
**Estimated Effort**: 2-3 days  
**Created**: 2025-10-25  
**Status**: Ready for Development

---

## User Story

**As a** user visiting the Graph RAG System,  
**I want** to register for a new account and log in with my credentials,  
**So that** I can access the career intelligence features and manage my session securely.

---

## Story Context

### Existing System Integration

- **Integrates with**: FastAPI backend authentication endpoints
- **Technology**: React, TailwindCSS, Headless UI, Fetch API
- **Follows pattern**: UI/UX specification at `docs/front-end-spec.md` (Login/Registration wireframes)
- **Touch points**: 
  - POST `/auth/register` endpoint
  - POST `/auth/login` endpoint
  - localStorage for JWT token storage
  - React Router for navigation/redirects

### Background

This is the foundation authentication implementation for the frontend. The backend already provides working authentication endpoints with JWT token generation. This story focuses solely on creating the user-facing login and registration screens with proper validation and error handling.

---

## Acceptance Criteria

### Functional Requirements

1. **Login Screen**
   - Display email and password input fields
   - Show "Login" primary button and "Register" secondary button
   - Accept email and password input
   - Submit credentials to POST `/auth/login` on form submit or Enter key
   - Store JWT token in localStorage on successful login
   - Redirect to Home page after successful login
   - Show error message for invalid credentials (401 response)
   - Show error message for network failures

2. **Registration Screen**
   - Display email and password input fields
   - Validate email format (standard email regex)
   - Validate password length (minimum 8 characters)
   - Show inline validation errors for invalid inputs
   - Submit to POST `/auth/register` on form submit or Enter key
   - Show error for duplicate email (400 response with "email already exists")
   - Show success message on successful registration
   - Redirect to login screen after successful registration
   - Show error message for network failures

3. **Form Validation**
   - Email field: Required, valid email format
   - Password field: Required, minimum 8 characters
   - Validation errors display inline below respective fields
   - Submit button disabled during API request (loading state)
   - Clear validation errors when user starts typing

4. **Responsive Design**
   - Works on mobile (375px - iPhone SE)
   - Works on tablet (768px - iPad)
   - Works on desktop (1280px - standard laptop)
   - Form is centered on screen at all breakpoints
   - Touch targets minimum 44x44px on mobile

### Integration Requirements

5. **API Integration**
   - POST `/auth/register` with request body: `{email: string, password: string}`
   - POST `/auth/login` with request body: `{email: string, password: string}`
   - Handle 200 response: `{token: string, user: {id, email}}`
   - Handle 400 response: `{error: string}` (validation error or duplicate email)
   - Handle 401 response: `{error: string}` (invalid credentials)
   - Handle 500 response: Generic error message
   - Handle network timeout: "Unable to connect. Please check your connection."

6. **Token Storage**
   - Store JWT token in localStorage with key: `authToken`
   - Store user data in localStorage with key: `user`
   - Tokens persist across page refreshes
   - Clear localStorage on logout (handled in future story)

7. **Navigation Integration**
   - Login screen accessible at `/login` route
   - Registration screen accessible at `/register` route
   - Login screen has "Don't have an account? Register" link → navigate to `/register`
   - Registration screen has "Already have an account? Login" link → navigate to `/login`
   - After successful login: navigate to `/home`
   - After successful registration: show success, navigate to `/login` after 2 seconds

### Quality Requirements

8. **Loading States**
   - Show spinner in submit button during API request
   - Disable form inputs during submission
   - Button text changes: "Login" → "Logging in..." or show spinner icon

9. **Error Handling**
   - All API errors display user-friendly messages (not raw error objects)
   - Validation errors are clear and actionable ("Email is required", "Password must be at least 8 characters")
   - Network errors provide retry guidance
   - Errors auto-clear when user corrects input

10. **Accessibility**
    - All form inputs have associated `<label>` elements
    - Form submission works with Enter key
    - Keyboard navigation (Tab key) follows logical order
    - Focus states visible on all inputs and buttons
    - Error messages associated with fields using `aria-describedby`
    - Screen reader announces validation errors

11. **Code Quality**
    - Components use React functional components with hooks
    - Form state managed with `useState`
    - API calls use async/await with try/catch
    - No hardcoded API URLs (use environment variable)
    - Follows ESLint and Prettier configuration
    - Code is commented for complex logic

---

## Technical Notes

### Integration Approach

```javascript
// API Integration Example
const handleLogin = async (email, password) => {
  try {
    setLoading(true);
    setError(null);
    
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Login failed');
    }
    
    const data = await response.json();
    localStorage.setItem('authToken', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    navigate('/home');
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

### Component Structure

```
src/
├── screens/
│   ├── Login.jsx          # Login screen component
│   └── Registration.jsx   # Registration screen component
├── components/
│   ├── AuthForm.jsx       # Reusable form container
│   ├── Input.jsx          # Reusable input field with validation
│   └── Button.jsx         # Reusable button component
├── services/
│   └── authService.js     # API service for auth endpoints
└── utils/
    └── validation.js      # Email/password validation utilities
```

### Existing Pattern Reference

- **UI/UX Spec**: `docs/front-end-spec.md` Section 6.1 (Login/Registration wireframes)
- **Design System**: TailwindCSS with colors defined in spec Section 7.2
- **Form Components**: Headless UI for accessible form elements

### Key Constraints

- Must use TailwindCSS utility classes (no custom CSS)
- JWT token stored in localStorage (httpOnly cookies deferred to post-MVP)
- No email verification for MVP (users can register and immediately login)
- No "Remember Me" checkbox for MVP
- No password strength indicator for MVP
- No "Forgot Password" flow for MVP

---

## Definition of Done

- [x] Login screen renders with email/password fields and submit button
- [x] Registration screen renders with email/password fields and validation
- [x] Form validation works (email format, password length)
- [x] API integration complete for `/auth/login` and `/auth/register`
- [x] JWT tokens stored in localStorage on successful login
- [x] Navigation works between login/registration screens
- [x] Redirect to Home page after successful login
- [x] Error handling covers all API error scenarios (400, 401, 500, network)
- [x] Loading states display during API requests
- [x] Responsive design tested on mobile (375px), tablet (768px), desktop (1280px)
- [x] Keyboard navigation works (Tab, Enter key)
- [x] Focus states visible on all interactive elements
- [x] Screen reader tested with VoiceOver (macOS)
- [x] Code reviewed and approved
- [x] Unit tests written for validation logic
- [x] Integration tests written for API calls (mocked)

---

## Risk Assessment

### Primary Risk

**Email validation regex doesn't catch all edge cases**

**Mitigation**: 
- Use standard email regex pattern (RFC 5322 compliant)
- Backend performs server-side validation as final check
- Display backend validation errors to user

### Secondary Risk

**Token storage in localStorage vulnerable to XSS attacks**

**Mitigation**:
- Acceptable for MVP (per PRD)
- Plan to migrate to httpOnly cookies post-MVP
- Implement Content Security Policy (CSP) headers
- No sensitive data stored beyond JWT token

### Rollback

- Remove login/registration routes from React Router
- Backend authentication endpoints unchanged (no rollback needed)
- Simple revert via Git

---

## Testing Strategy

### Manual Testing Checklist

**Login Flow:**
- [ ] Login with valid credentials → success, redirect to /home
- [ ] Login with invalid email → error: "Invalid credentials"
- [ ] Login with invalid password → error: "Invalid credentials"
- [ ] Login with empty fields → validation errors
- [ ] Login with network disconnected → error: "Unable to connect"

**Registration Flow:**
- [ ] Register with valid email/password → success, redirect to /login
- [ ] Register with duplicate email → error: "Email already registered"
- [ ] Register with invalid email format → validation error
- [ ] Register with password < 8 chars → validation error
- [ ] Register with empty fields → validation errors

**Responsive Design:**
- [ ] Test on iPhone SE (375px) - form centered, readable
- [ ] Test on iPad (768px) - form centered, good spacing
- [ ] Test on desktop (1280px) - form centered, optimal width

**Accessibility:**
- [ ] Tab through form - all fields and buttons focusable
- [ ] Press Enter on login button - submits form
- [ ] Screen reader announces field labels and errors
- [ ] Focus ring visible on all interactive elements

### Automated Testing

**Unit Tests (Jest + React Testing Library):**
```javascript
describe('Login Component', () => {
  it('displays validation error for invalid email', () => {...});
  it('displays validation error for short password', () => {...});
  it('disables button during submission', () => {...});
  it('displays API error message on failed login', () => {...});
});
```

**Integration Tests:**
```javascript
describe('Login API Integration', () => {
  it('calls /auth/login with correct payload', () => {...});
  it('stores token in localStorage on success', () => {...});
  it('navigates to /home on successful login', () => {...});
});
```

---

## Dependencies

- Backend `/auth/register` and `/auth/login` endpoints deployed
- Environment variable `REACT_APP_API_BASE_URL` configured
- TailwindCSS and Headless UI installed
- React Router configured

---

## Follow-up Stories

- EPIC-001-STORY-002: Application Shell (Navigation, Routing, Home Dashboard)
- EPIC-001-STORY-003: Authentication Flow & Route Protection

---

**Story Status**: ✅ Ready for Development
