# E2E Testing Checklist

## Test Environment Setup
- [ ] Backend running on `http://localhost:8000`
- [ ] Frontend running on `http://localhost:5173`
- [ ] Neo4j database running and connected
- [ ] PostgreSQL database running and connected
- [ ] Test data CSVs uploaded (skills and jobs)
- [ ] Fresh test user created for this test run

**Tester Name**: ___________
**Test Date**: ___________
**Environment**: Development/Staging/Production

---

## Test Scenario 1: User Registration Flow

### Test Steps
- [ ] Navigate to `/register` page
- [ ] Enter email: `test@example.com`
- [ ] Enter password: `securepassword123`
- [ ] Click "Register" button
- [ ] **Expected**: Success message or redirect to login page
- [ ] Navigate to login page (if not auto-redirected)
- [ ] Login with new credentials (email: `test@example.com`, password: `securepassword123`)
- [ ] **Expected**: Redirect to `/chat` page
- [ ] Verify chat interface is displayed

### Results
- **Result**: [ ] PASS [ ] FAIL
- **Notes**: ___________________________________________
- **Screenshots**: ___________________________________________
- **Issues Found**: ___________________________________________

---

## Test Scenario 2: CSV Upload Flow

### 2A: Skills CSV Upload

#### Test Steps
- [ ] Navigate to `/upload` page
- [ ] Click "Upload Skills" or select skills upload section
- [ ] Select `test-data/skills_sample.csv` file
- [ ] Click "Upload" button
- [ ] **Expected**: File validation passes
- [ ] **Expected**: Preview table shows uploaded data
- [ ] Review preview data for accuracy
- [ ] Click "Confirm" button to start ingestion
- [ ] **Expected**: Ingestion progress bar appears
- [ ] Monitor progress until completion
- [ ] **Expected**: "Upload complete" or success message shown
- [ ] Verify success message contains record count

#### Results
- **Result**: [ ] PASS [ ] FAIL
- **Upload Time**: _____ seconds
- **Records Processed**: _____
- **Notes**: ___________________________________________
- **Issues Found**: ___________________________________________

### 2B: Jobs CSV Upload

#### Test Steps
- [ ] Navigate to `/upload` page (or stay on current page)
- [ ] Click "Upload Jobs" or select jobs upload section
- [ ] Select `test-data/jobs_sample.csv` file
- [ ] Click "Upload" button
- [ ] **Expected**: File validation passes
- [ ] **Expected**: Preview table shows uploaded data
- [ ] Review preview data for accuracy
- [ ] Click "Confirm" button to start ingestion
- [ ] **Expected**: Ingestion progress bar appears
- [ ] Monitor progress until completion
- [ ] **Expected**: "Upload complete" or success message shown
- [ ] Verify success message contains record count

#### Results
- **Result**: [ ] PASS [ ] FAIL
- **Upload Time**: _____ seconds
- **Records Processed**: _____
- **Notes**: ___________________________________________
- **Issues Found**: ___________________________________________

---

## Test Scenario 3: Query Flow

### Test Steps
- [ ] Navigate to `/chat` page
- [ ] Verify chat interface is displayed
- [ ] Enter query in input field: `What skills are needed for Data Scientist jobs?`
- [ ] Click "Send" button or press Enter
- [ ] **Expected**: Loading indicator appears
- [ ] **Expected**: User message appears in chat
- [ ] **Expected**: Assistant response appears within 5 seconds
- [ ] Verify response is relevant to the query
- [ ] **Expected**: Sources section displays below response
- [ ] Click to expand sources section
- [ ] **Expected**: Source details shown (jobs, skills, companies, etc.)
- [ ] Verify sources are relevant to the response
- [ ] Check that source data includes job titles, skill names, etc.

### Results
- **Result**: [ ] PASS [ ] FAIL
- **Response Time**: _____ seconds
- **Response Quality**: [ ] Excellent [ ] Good [ ] Poor
- **Sources Displayed**: [ ] YES [ ] NO
- **Sources Relevant**: [ ] YES [ ] NO
- **Notes**: ___________________________________________
- **Response Text**: ___________________________________________
- **Issues Found**: ___________________________________________

---

## Test Scenario 4: Multi-Turn Conversation

### Test Steps
- [ ] Navigate to `/chat` page (or continue from Scenario 3)
- [ ] Clear previous conversation if needed
- [ ] Enter first query: `Tell me about Python`
- [ ] Click "Send" or press Enter
- [ ] **Expected**: Response appears describing Python
- [ ] Verify response quality
- [ ] Enter follow-up query: `What jobs require it?`
- [ ] Click "Send" or press Enter
- [ ] **Expected**: Response mentions Python-related jobs
- [ ] **Expected**: Response shows contextual awareness (references Python from previous message)
- [ ] Verify response is contextually relevant

### Results
- **Result**: [ ] PASS [ ] FAIL
- **Context Maintained**: [ ] YES [ ] NO [ ] PARTIAL
- **Response Quality**: [ ] Excellent [ ] Good [ ] Poor
- **Notes**: ___________________________________________
- **First Response**: ___________________________________________
- **Follow-up Response**: ___________________________________________
- **Issues Found**: ___________________________________________

**Note**: For MVP, full conversation history may not be passed to LLM. Basic session memory is acceptable.

---

## Test Scenario 5: Error Handling

### 5A: Invalid Login

#### Test Steps
- [ ] Navigate to `/login` page
- [ ] Logout if currently logged in
- [ ] Enter valid email: `test@example.com`
- [ ] Enter wrong password: `wrongpassword123`
- [ ] Click "Login" button
- [ ] **Expected**: Error message displayed (e.g., "Invalid credentials")
- [ ] **Expected**: User NOT redirected (stays on login page)
- [ ] Verify error message is user-friendly

#### Results
- **Result**: [ ] PASS [ ] FAIL
- **Error Message Shown**: [ ] YES [ ] NO
- **Error Message Text**: ___________________________________________
- **Notes**: ___________________________________________

### 5B: Empty Query

#### Test Steps
- [ ] Navigate to `/chat` page
- [ ] Ensure input field is empty
- [ ] Click "Send" button or press Enter
- [ ] **Expected**: Input validation prevents sending OR error message shown
- [ ] Verify user-friendly message (e.g., "Please enter a message")

#### Results
- **Result**: [ ] PASS [ ] FAIL
- **Validation Behavior**: ___________________________________________
- **Notes**: ___________________________________________

### 5C: API Failure Simulation

#### Test Steps
- [ ] Open terminal/command prompt
- [ ] Stop backend server (kill backend process or `docker-compose down backend`)
- [ ] Navigate to `/chat` page in browser
- [ ] Enter query: `Test query`
- [ ] Click "Send" button
- [ ] **Expected**: Graceful error message shown (e.g., "Unable to connect to server" or "Service temporarily unavailable")
- [ ] **Expected**: NO raw error stack traces visible to user
- [ ] Restart backend server
- [ ] Try sending query again
- [ ] **Expected**: Query works normally after backend restart

#### Results
- **Result**: [ ] PASS [ ] FAIL
- **Error Message Shown**: [ ] YES [ ] NO
- **Error Message User-Friendly**: [ ] YES [ ] NO
- **Error Message Text**: ___________________________________________
- **Raw Errors Visible**: [ ] YES [ ] NO
- **Notes**: ___________________________________________

---

## Overall Test Results

### Summary Statistics
- **Total Test Scenarios**: 5
- **Scenarios Passed**: _____
- **Scenarios Failed**: _____
- **Total Test Steps Executed**: _____
- **Test Duration**: _____ minutes

### Issue Severity Breakdown
- **Blocker Issues** (prevent MVP launch): _____
  - Issue IDs: ___________________________________________
- **Critical Issues** (major functionality broken): _____
  - Issue IDs: ___________________________________________
- **Major Issues** (important but not blocking): _____
  - Issue IDs: ___________________________________________
- **Minor Issues** (cosmetic or low impact): _____
  - Issue IDs: ___________________________________________

### Performance Metrics
- **Average Query Response Time**: _____ seconds
- **Skills CSV Upload Time**: _____ seconds
- **Jobs CSV Upload Time**: _____ seconds
- **Page Load Times**:
  - Login: _____ seconds
  - Chat: _____ seconds
  - Upload: _____ seconds

### Browser/Environment Details
- **Browser**: ___________________________________________
- **Browser Version**: ___________________________________________
- **Operating System**: ___________________________________________
- **Screen Resolution**: ___________________________________________
- **Network Speed**: ___________________________________________

---

## Known Issues Log

### Issue Template
Use this format to document each issue found:

**BUG-001**
- **Severity**: Blocker / Critical / Major / Minor
- **Scenario**: Test Scenario X - [Name]
- **Description**: Brief description of the issue
- **Steps to Reproduce**:
  1. Step 1
  2. Step 2
  3. ...
- **Expected**: What should happen
- **Actual**: What actually happened
- **Screenshots/Logs**: [Attach or reference]
- **Environment**: Browser, OS, etc.
- **Workaround**: If any temporary fix exists
- **Status**: Open / In Progress / Resolved / Won't Fix
- **Assigned To**: ___________
- **Resolution**: How it was fixed (if resolved)

---

## MVP Approval Criteria

### Required for Approval
- [ ] All 5 test scenarios passing
- [ ] No blocker issues remaining
- [ ] All critical issues fixed or have documented workarounds
- [ ] Average query response time < 5 seconds
- [ ] CSV upload completes successfully for both skills and jobs
- [ ] Error messages are user-friendly (no raw stack traces)
- [ ] No console errors on happy path (check browser console)

### Optional but Recommended
- [ ] Screenshots captured for key flows
- [ ] Performance metrics documented
- [ ] All minor issues documented for post-MVP
- [ ] Regression testing completed (previous features still work)

---

## Final Approval

### Sign-off
- **Tested By**: ___________________________________________
- **Test Date**: ___________________________________________
- **Test Environment**: Development / Staging / Production
- **Overall Result**: [ ] APPROVED FOR MVP [ ] NOT APPROVED
- **Approval Notes**: ___________________________________________
- **Next Steps**: ___________________________________________

### Approver Sign-off
- **Approved By**: ___________________________________________
- **Approval Date**: ___________________________________________
- **Signature**: ___________________________________________

---

## Regression Testing Notes

If this is a regression test (re-testing after fixes), document:
- **Previous Test Date**: ___________________________________________
- **Issues Fixed Since Last Test**: ___________________________________________
- **New Issues Found**: ___________________________________________
- **Regression Issues** (previously working features broken): ___________________________________________

---

## Additional Notes and Observations

Use this section for any additional observations, suggestions, or comments:

___________________________________________
___________________________________________
___________________________________________
___________________________________________
___________________________________________
