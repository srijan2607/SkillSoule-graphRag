# Story: Application Shell (Navigation, Routing, Home Dashboard)

**Story ID**: EPIC-001-STORY-002  
**Epic**: Epic 1 - Authentication & Core Layout  
**Priority**: High  
**Estimated Effort**: 2-3 days  
**Dependencies**: EPIC-001-STORY-001 (Authentication Screens)  
**Status**: Ready for Development

---

## User Story

**As an** authenticated user,  
**I want** a clear home dashboard with navigation to key features,  
**So that** I can easily access chat and data upload functionality.

---

## Acceptance Criteria

### Functional Requirements

1. **Home Page Dashboard**
   - Display page title: "Career Intelligence"
   - Show two large action cards: "Start Chatting" and "Upload Data"
   - "Start Chatting" card: Icon (chat bubble), title, description ("Ask questions about careers, skills, and jobs")
   - "Upload Data" card: Icon (upload/cloud), title, description ("Upload Skills or Jobs CSV files")
   - Optional: Quick stats display (jobs count, skills count, last updated)
   - Cards clickable → navigate to `/chat` and `/upload` respectively
   - Hover state: card elevation increases, border highlights

2. **Top Navigation Bar**
   - Fixed position at top of viewport
   - Logo/brand "Career Intelligence" (left) → click returns to Home
   - Navigation links: "Home", "Chat", "Upload Data" (center/left-aligned)
   - User menu (right): User email + dropdown with "Logout" option
   - Active route highlighted (underline or background)
   - Navigation persists across all authenticated screens

3. **Mobile Navigation**
   - Hamburger menu (☰) on mobile (<768px)
   - Tap hamburger → slide-in menu with links
   - Links: Home, Chat, Upload Data, Logout
   - Tap outside menu or X icon → closes menu
   - User profile icon (right) shows on mobile

4. **Routing Setup**
   - `/` → redirects to `/home` (if authenticated) or `/login` (if not)
   - `/home` → Home dashboard (protected route)
   - `/chat` → Chat interface (protected route, future story)
   - `/upload` → Upload data screen (protected route, future story)
   - `/login` → Login screen (from EPIC-001-STORY-001)
   - `/register` → Registration screen (from EPIC-001-STORY-001)

5. **Logout Functionality**
   - Click "Logout" in user menu → clears localStorage (`authToken`, `user`)
   - Redirects to `/login` after logout
   - Optional: Show confirmation dialog before logout

### Integration Requirements

6. **Authentication Context**
   - Create React Context for global auth state
   - Context provides: `user`, `token`, `login()`, `logout()`, `isAuthenticated`
   - `login()` sets user and token in context + localStorage
   - `logout()` clears user and token from context + localStorage
   - `isAuthenticated` checks if token exists in localStorage

7. **React Router Integration**
   - Use React Router v6 for routing
   - Protected routes redirect to `/login` if not authenticated
   - Public routes (login, register) accessible without auth
   - Navigation uses `<Link>` components (not `<a>` tags)

### Quality Requirements

8. **Responsive Design**
   - Desktop (≥1024px): Full horizontal navigation, two-column card layout
   - Tablet (768px-1023px): Full horizontal navigation, two-column card layout
   - Mobile (<768px): Hamburger menu, single-column card layout
   - Cards: full-width on mobile, 50% width on tablet/desktop

9. **Accessibility**
   - Navigation keyboard accessible (Tab through links)
   - Hamburger menu keyboard accessible (Enter to open, ESC to close)
   - User menu dropdown keyboard accessible (arrow keys, Enter to select)
   - Focus states visible on all interactive elements
   - Screen reader announces navigation links and current page

10. **Performance**
    - Code split routes using React.lazy() for chat and upload screens
    - Suspense fallback shows loading spinner during route load
    - Navigation bar renders instantly (no layout shift)

---

## Technical Notes

### Component Structure

```
src/
├── context/
│   └── AuthContext.jsx      # Global auth state
├── screens/
│   └── Home.jsx              # Home dashboard
├── components/
│   ├── Navigation.jsx        # Top navigation bar
│   ├── MobileMenu.jsx        # Mobile hamburger menu
│   ├── UserMenu.jsx          # User dropdown menu
│   └── ActionCard.jsx        # Reusable action card
├── routes/
│   ├── AppRoutes.jsx         # Main routing configuration
│   └── ProtectedRoute.jsx    # Protected route wrapper
└── App.jsx                   # Root component with AuthProvider
```

### AuthContext Example

```javascript
const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  
  const [token, setToken] = useState(() => localStorage.getItem('authToken'));
  
  const login = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('authToken', authToken);
  };
  
  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('user');
    localStorage.removeItem('authToken');
  };
  
  const isAuthenticated = !!token;
  
  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

---

## Definition of Done

- [x] Home dashboard renders with 2 action cards
- [x] Navigation bar displays with logo, links, user menu
- [x] Mobile hamburger menu works (<768px)
- [x] Action cards navigate to `/chat` and `/upload`
- [x] Active route highlighted in navigation
- [x] Logout clears localStorage and redirects to `/login`
- [x] AuthContext provides global auth state
- [x] React Router configured with protected routes
- [x] Responsive design tested (mobile, tablet, desktop)
- [x] Keyboard navigation works
- [x] Screen reader tested

---

## Dependencies

- EPIC-001-STORY-001 (Authentication Screens) must be completed
- React Router installed (`react-router-dom`)
- Heroicons installed for icons

---

**Story Status**: ✅ Ready for Development
