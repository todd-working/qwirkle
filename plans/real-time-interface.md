# Real-Time Game Interface Improvements

## Overview
Incremental improvements to the web UI, each task independently testable.

---

## Task 1: Fixed UI Layout (Scrollable Board Only)
**Goal:** UI elements (sidebar, hand, controls) stay fixed; only the board scrolls/pans.

**Test:**
- Play a game with many tiles on board
- Scroll/pan the board area
- Verify sidebar, hand, and controls don't move
- Verify you can still drag tiles from hand to board

**Implementation:**
- Wrap board in a scrollable container with `overflow: auto`
- Keep sidebar, hand, and controls in fixed position layout
- Adjust z-index so drag overlay appears above everything

---

## Task 2: Desktop-Only Optimization
**Goal:** Remove mobile responsiveness, optimize for desktop experience.

**Test:**
- Open game in desktop browser (1200px+ width)
- Verify tiles, board, and controls are appropriately sized
- No cramped mobile layouts

**Implementation:**
- Remove responsive breakpoints for mobile
- Set minimum widths for components
- Increase default tile sizes for better visibility
- Remove touch-specific handlers (keep drag-drop which works for both)

---

## Task 3: Beginner/Normal Game Modes
**Goal:** Two modes selectable at game start.

**Beginner Mode (default):**
- Shows valid placement positions when tile selected
- Hint button available
- Score preview shown on hover

**Normal Mode:**
- No valid position highlighting
- No hint button
- No score preview (just place and see)

**Test:**
1. Start new game in Beginner mode
   - Click tile in hand, see green highlights on valid positions
   - Click "Hint" button, see AI suggestion
   - Hover over valid position, see score preview
2. Start new game in Normal mode
   - Click tile in hand, no highlights appear
   - No "Hint" button visible
   - No score preview on hover

**Implementation:**
- Add mode selector to new game dialog
- Store mode in game state
- Conditionally render hints/highlights based on mode

---

## Task 4: Animate AI Moves
**Goal:** When AI plays, tiles animate from off-screen onto the board.

**Test:**
1. Start Human vs AI game
2. Make a move as human
3. Watch AI's tiles animate onto the board (slide in from side)
4. Verify animation completes before player can act

**Implementation:**
- After AI move response, delay state update
- Animate each tile placement sequentially (200-300ms each)
- Use CSS transitions or framer-motion
- Disable player interaction during animation

---

## Task 5: Win Probability Display
**Goal:** Show each player's win probability based on current game state.

**Display:**
- Small bar or percentage next to each player's score
- Updates after each move
- Based on: score difference, tiles in hand, tiles remaining

**Test:**
1. Start a game
2. See initial win probability (~50/50)
3. Make moves and watch probability shift
4. When one player leads significantly, their probability should be higher

**Implementation:**
- Backend endpoint: `GET /api/game/{id}/win-probability`
- Simple heuristic formula (can be replaced with ML later):
  ```
  score_advantage = (my_score - opponent_score) / max(total_score, 1)
  hand_potential = estimate_hand_value(my_hand) - estimate_hand_value(opponent_hand)
  game_progress = 1 - (bag_remaining / 108)

  raw_prob = 0.5 + (score_advantage * 0.3) + (hand_potential * 0.1 * game_progress)
  win_prob = clamp(raw_prob, 0.05, 0.95)
  ```
- Frontend: fetch after each move, display as progress bar

---

## Implementation Order

Each task builds on the previous but is independently testable:

```
Task 1 (Fixed Layout) → Can test immediately
    ↓
Task 2 (Desktop) → Can test with Task 1
    ↓
Task 3 (Game Modes) → New game flow, testable independently
    ↓
Task 4 (AI Animation) → Requires AI game, testable after Task 3
    ↓
Task 5 (Win Probability) → Backend + frontend, testable after any above
```

---

## Verification Checklist

After each task, verify:
- [ ] Game still loads without errors
- [ ] Can start new game
- [ ] Can drag and drop tiles
- [ ] Can play complete game to end
- [ ] New feature works as described in Test section
