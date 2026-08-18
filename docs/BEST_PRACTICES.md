# AMH Lab Tracker - Best Practices

This document outlines the coding standards and design principles that all developers must adhere to when contributing to the AMH Lab Tracker.

## 1. UI & Design Rules

*   **No Emojis:** Do not use emojis anywhere in the user interface, documentation, or codebase (including comments and commit messages).
*   **Icons:** Only use **Lucide icons**. Do not mix icon sets.
*   **No Pill Tags or Badges:** Avoid using pill tags or badges. Use plain text to represent statuses and tags, as badges are rarely necessary and can clutter the interface.
*   **Simplicity:** Prioritize a clean, function-driven design that favors maximum legibility and plain text over decorative elements.

## 2. General Guidelines

*   *This document will be updated as the project evolves. Always refer back to this file for the latest coding and design standards.*

## 3. Development Philosophy

### Avoid Large Code Refactors
Unless completely necessary and warranted, developers **must** avoid large code refactors. 

### Small, Surgical Changes
Always make small, targeted changes to implement new features, fix bugs, or modify an existing feature. Do not attempt a full rewrite of existing logic or UI components when a surgical insertion or removal will suffice.

## 4. Terminology

*   **Client vs Patient:** Always use the term **'Client'**, never 'Patient'. This generalizes testing to include routine checkups and non-pathological testing, as not everyone in the lab is suffering from an illness.
