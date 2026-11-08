# Task: Implement a UI in the style of the new Microsoft 365 Copilot app

## Design philosophy (from the Microsoft Design article)
1. Intent first: make conversation/the input box the primary entry point. Users state a goal first, and the system surfaces the right tools and content, instead of making users hunt through menus.
2. Reduce cognitive load: restrained, spacious, one primary task emphasized per screen. The goal is to bring calm and focus to a noisy workday.
3. Adaptive, not static: the interface flexes with user intent. Tools appear when needed and recede when done.
4. Verbs over icons: entry points and button labels use actions ("Draft", "Summarize", "Analyze"), not decorative icons alone.
5. Human-AI collaboration: AI output always sits next to editable space. The user is the conductor, not a passive recipient.

## Visual specification
(Elements visible in the article's imagery plus reasonable inference; exact colors and sizes are suggestions and can be adjusted.)
- Overall: light theme by default, with a very soft pastel gradient background (pale lavender / blue / pink). Content sits on white or semi-transparent cards.
- Color: low saturation, few colors. Use the accent color only for primary buttons and focus states; everything else is neutral grayscale.
- Typography: sans-serif. Prefer "Segoe UI Variable", fall back to system-ui. Build hierarchy with size and weight, not color.
- Shape: generous corner radii (cards 12-16px, inputs/buttons 8-12px or pill), very light shadows or 1px hairline borders. Avoid heavy shadows and thick borders.
- Spacing: 4/8px grid, generous whitespace.
- Icons: outline style, consistent stroke weight, always paired with a text label.

## Layout and structure
- Left sidebar: collapsible navigation (Chat, Agents, Pages, etc.) using accordion-style groups. When collapsed, show icons only.
- Home / empty state: centered large greeting (e.g., "Hi, how can I help you?"), a wide input box, and a few suggested-task cards. Clicking a card fills the input.
- Main area: Chat is the core. Support a side-by-side layout of chat + document/content, with a draggable divider and a one-click way to collapse the chat pane.
- Contextual tools: when the user selects AI-generated content (an image, a block of text), show a floating toolbar for relevant edits next to it, rather than a permanent wall of toolbars.

## Interaction and motion
- Restrained motion: 150-250ms fade, slide, and expand/collapse transitions with ease-out. Respect prefers-reduced-motion.
- AI generation: streamed output plus a subtle "thinking" state. No flashy loading animations.
- Input box: auto-grows, Enter to send, Shift+Enter for newline. Attachments and @mentions live inside the input as secondary actions.
- Agent selection: present agents as cards or a dropdown with a one-line description of what each does, reinforcing "the right agent for the right job."

## Non-functional requirements
- Accessibility: WCAG AA contrast, full keyboard navigation, visible focus rings, ARIA labels, screen reader support.
- Responsive: on narrow screens the sidebar becomes a drawer and the split view becomes a single-pane toggle.
- Dark mode: implemented through CSS variables / design tokens. All colors must go through tokens.

## Implementation instructions
- Define design tokens first (color, radius, spacing, shadow, typography, motion duration), then build components.
- Component breakdown: Sidebar, ChatInput, SuggestionCard, ChatThread, SplitPane, ContextToolbar.
- Implement the home empty state and sidebar first and show me the result. After I confirm, build the split view and contextual toolbar.
- Do not use any Microsoft trademarks, logos, or Copilot branding. Borrow the style only.