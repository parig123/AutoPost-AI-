# Calendar Overhaul - Implementation Tracker

## Step 1: Fix Critical Calendar Bugs
- [ ] Fix editorPanel ID mismatch (editorPanel → postEditorPanel)
- [ ] Fix FullCalendar eventSources double declaration
- [ ] Implement handleContextAction() for context menu
- [ ] Wire up closeEditor button

## Step 2: Build AI Natural Language Scheduling Endpoint
- [ ] Add parse_nlp method to AIGenerator service
- [ ] Create POST /api/schedule/parse-nlp endpoint
- [ ] Integrate NLP quick add in calendar.js

## Step 3: Make Ideas Bin Interactive (Drag & Drop)
- [ ] Add draggability to ideas in sidebar
- [ ] Handle drop on calendar to create scheduled draft
- [ ] Add delete button for each idea

## Step 4: Make AI Suggestions Clickable
- [ ] Click suggestion to open editor pre-filled
- [ ] Add "Accept Suggestion" flow
- [ ] Style suggestions distinctly (dashed, sparkle)

## Step 5: Add Conflict Detection & Smart Warnings
- [ ] Check for posts within 2-hour window
- [ ] Show warning toast on conflict
- [ ] Enhance heatmap for multiple posts

## Step 6: Connect Queue Status to Calendar
- [ ] Status badges on events (color + icon)
- [ ] Quick actions for Pending Approval posts
- [ ] Published posts non-editable with LinkedIn icon

## Step 7: Timezone-Aware Scheduling & Polish
- [ ] UTC storage with local display
- [ ] datetime-local timezone handling
- [ ] Loading states, error toasts, smooth transitions
