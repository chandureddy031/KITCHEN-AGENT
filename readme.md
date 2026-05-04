# Smart Kitchen AI

An AI-powered kitchen management and meal planning application built with FastAPI, LangGraph, and Groq LLM. Users can manage their grocery inventory, plan meals for any number of days, follow step-by-step cooking instructions with a built-in timer, and rate completed recipes for community recommendations.

---
## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [LangGraph Agent Pipeline](#langgraph-agent-pipeline)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage Flow](#usage-flow)
- [Screenshots](#screenshots)
- [API Endpoints](#api-endpoints)
- [Technologies Used](#technologies-used)

---

## Overview

Smart Kitchen AI solves a common household problem: you have a set of groceries and a family to feed, but you do not know how long the groceries will last or what meals to prepare. This application takes your current inventory, analyzes daily consumption based on family size and appetite, generates a full meal plan for your target number of days, and then walks you through each recipe step by step with a human-in-the-loop cooking experience.

Each user has their own isolated set of "kitchens" (up to 10), each containing independent grocery inventories, family configurations, meal plans, and cooking progress. One user's data is completely invisible to another.

---

## Features

**User Authentication**
- Sign up with a display name, username, email, and password
- Log in with username or email
- Session-based authentication using HTTP-only cookies
- Per-user data isolation across all kitchen stores

**Kitchen Management**
- Create up to 10 independent kitchen stores per user
- Each store has its own groceries, family members, meal plan, and cooking state
- Edit existing kitchens (name, groceries, family) with automatic re-analysis on save
- Delete kitchens with a confirmation modal

**AI-Powered Analysis**
- Inventory analysis: estimates daily consumption per item based on family size and appetite levels (light, medium, heavy)
- Duration calculation: determines how many days current groceries will last
- Meal planning: generates breakfast, lunch, and dinner for each target day
- Recipe generation: creates detailed step-by-step cooking instructions with timings and tips

**Step-by-Step Cooking Mode**
- One step displayed at a time with a "Done" and "Not Yet" button (human-in-the-loop)
- Built-in countdown timer for each step
- Progress bar showing overall completion
- Step overview panel for quick navigation
- Completion celebration with confetti animation

**Rating and Community Recommendations**
- Star rating (1-5) with text comments after completing a recipe
- Community recipe board showing top-rated meals across all users
- Recent reviews feed

**User Profile**
- Upload a profile avatar (resized to 200x200 and stored as base64)
- Set a display name that appears in the welcome greeting
- Write a personal bio
- Profile dropdown menu in the navigation bar

**Ingredient Visualization**
- Each grocery item is enriched with an emoji and an Unsplash image
- Over 50 ingredients mapped with metadata
- Images displayed in the inventory dashboard with fallback to emoji

---

## Architecture

The application follows a three-layer architecture:


**Frontend Layer**: Jinja2 templates served by FastAPI. Each page is a single HTML file with embedded JavaScript for dynamic behavior. CSS is centralized in `base.html` with CSS custom properties for theming. No frontend framework is used; all interactivity is vanilla JavaScript with fetch API calls to the backend.

**Backend Layer**: FastAPI handles HTTP routing, authentication middleware, and data validation. It delegates AI tasks to the LangGraph agent and persistence to the storage module. Authentication uses SHA-256 password hashing with per-user salts and token-based session management via HTTP-only cookies.

**AI Agent Layer**: LangGraph orchestrates a state graph of LLM-powered nodes. Each node performs a specific analysis task (inventory analysis, duration calculation, meal suggestion, recipe generation). The Groq API provides fast inference using the Llama 3.3 70B model. Each node has a fallback heuristic in case the LLM call fails.

**Storage Layer**: A single JSON file (`database/data.json`) stores all application data. Thread-safe read/write operations are handled with a threading lock. The data model includes users, authentication tokens, kitchen stores, ratings, and community recipe aggregates.

---

## LangGraph Agent Pipeline

The AI agent is built as a LangGraph `StateGraph` with typed state management. The state is defined as a `TypedDict` containing fields for groceries, family data, daily consumption estimates, meal plans, recipe steps, and cooking progress.

### Main Analysis Graph

The compiled graph used for initial kitchen analysis contains three nodes connected in a linear pipeline:


---

## Setup and Installation

**Prerequisites**
- Python 3.10 or higher
- A Groq API key (set in `backend/agent.py`)

**Steps**

1. Clone or download the project directory.

2. Install dependencies:

5. Open a browser and navigate to `http://localhost:8000`.

The application automatically creates the `database/data.json` file and required directories on first run.

---

## Usage Flow

**Step 1: Sign Up**
A new user creates an account by providing a display name, username, email, and password. The display name is used throughout the application for personalized greetings.

**Step 2: Create a Kitchen**
From the home page, the user clicks "New Kitchen" and enters a name for the kitchen, adds all available grocery items with quantities and units, and adds family members with their ages and appetite levels.

**Step 3: AI Analysis**
Upon submission, the LangGraph agent analyzes the inventory, estimates daily consumption for each item, and calculates how many days the groceries will last. This information is displayed on the kitchen dashboard.

**Step 4: Generate Meal Plan**
The user sets a target number of days and clicks "Generate Meal Plan." The AI creates breakfast, lunch, and dinner for each day using the available ingredients.

**Step 5: Cook a Meal**
The user selects a meal from the plan. The AI generates detailed step-by-step instructions. Each step is shown one at a time with a description, duration, tips, and a countdown timer. The user clicks "Done" to advance to the next step or "Not Yet" to stay on the current step.

**Step 6: Rate and Review**
After completing a recipe, the user is prompted to rate it (1-5 stars) and leave a comment. Ratings contribute to a community recipe board visible to all users.

**Step 7: Manage Kitchens**
Users can create up to 10 kitchens, edit existing ones (which resets the meal plan and re-analyzes), and delete kitchens they no longer need. Each kitchen maintains independent state.

---

## Screenshots

### Login Page

![Login Page](images/Screenshot%202026-05-04%20171435.png)

The login page presents a split-screen layout. The left side displays the application tagline with floating ingredient illustrations. The right side contains the login form with fields for username/email and password. New users can navigate to the sign-up page via a link at the bottom of the form.

### Home Page - Kitchen Listing

![Home Page](images/Screenshot%202026-05-04%20171456.png)

The home page displays a personalized welcome message using the user's display name. Below, a grid of kitchen store cards shows each kitchen's name, number of ingredients, family members, estimated days, and whether a meal plan has been generated. Each card has View, Edit, and Delete actions. The page shows the current count of kitchens used out of the maximum of 10.

### Create Kitchen Form

![Create Kitchen](images/Screenshot%202026-05-04%20171509.png)

The create kitchen form allows the user to name their kitchen, add grocery items with name/quantity/unit using a row of input fields, and add family members with name/age/appetite using a similar input row. Added items appear as removable tag chips below each section. The form validates that at least one grocery item and one family member are present before submission.

### Kitchen Dashboard

![Dashboard](images/Screenshot%202026-05-04%20171523.png)

The dashboard shows three stat cards (ingredients, family members, estimated days) at the top. Below, the inventory grid displays each ingredient in a card with its Unsplash image or emoji fallback, name, and quantity. A daily usage section shows estimated per-item consumption. At the bottom, the user can set a target number of days and generate a meal plan, which appears as a tabbed day selector with breakfast/lunch/dinner cards for each day.

### Cooking Mode

![Cooking Mode](images/Screenshot%202026-05-04%20171606.png)

Cooking mode displays one step at a time with a large step number, title, description, duration badge, and a tips section. A countdown timer is available for each step. Two action buttons allow the user to confirm completion ("Done - Next") or indicate they need more time ("Not Yet"). A progress bar at the top tracks overall completion. Below the main step card, an "All Steps" overview allows quick navigation to any step, and an "Ingredients" section lists everything needed for the recipe.

---

## API Endpoints

**Authentication**
- POST /api/auth/signup - Create a new user account
- POST /api/auth/login - Log in and receive an auth cookie
- POST /api/auth/logout - Log out and clear the auth cookie

**Profile**
- GET /api/profile - Get current user's profile
- PUT /api/profile - Update display name, bio, or avatar

**Kitchen Stores**
- GET /api/stores - List all kitchens for the current user
- POST /api/stores - Create a new kitchen (triggers AI analysis)
- GET /api/stores/{store_id} - Get a specific kitchen's full data
- PUT /api/stores/{store_id} - Update a kitchen (resets meal plan, re-analyzes)
- DELETE /api/stores/{store_id} - Delete a kitchen

**Meal Planning and Cooking**
- POST /api/stores/{store_id}/plan - Generate meal plan for target days
- POST /api/stores/{store_id}/select-meal - Select a meal and generate recipe steps
- POST /api/stores/{store_id}/complete-step - Mark current cooking step as done

**Ratings**
- POST /api/rate - Submit a rating for a completed recipe
- GET /api/ratings - Get recent ratings across all users
- GET /api/community - Get community recipe rankings

---

## Technologies Used

- **FastAPI** - Async Python web framework for the backend API and template serving
- **LangGraph** - State graph framework for orchestrating multi-step AI agent pipelines
- **LangChain + Groq** - LLM integration layer using Groq's Llama 3.3 70B model for fast inference
- **Jinja2** - Server-side HTML templating
- **Vanilla JavaScript** - Frontend interactivity without frameworks
- **CSS Custom Properties** - Theming and responsive design with glassmorphism aesthetic
- **JSON File Storage** - Lightweight persistence with thread-safe read/write operations
- **SHA-256 Hashing** - Password security with per-user salts
