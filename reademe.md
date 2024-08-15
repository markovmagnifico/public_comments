# Public Comments

This repo is intended as tooling to help public sector employees review comments on NPRMs.
NPRMs are posted at: https://www.federalregister.gov/
Comments are posted at: https://www.regulations.gov/

# Plan

- Set up OpenAI and/or Claude APIs

- Build out scripting capabilities to scrape the data

  - Core NPRM document
  - Comments
  - Attached documents from comments (e.g. PDF), and parsing the data from them
  - Organize the way these files are downloaded

- Local DB for storing info on where all these files are saved locally

- Indexing the core NPRM Document

  - To help with the size of these documents and to provide accurate quotes, we need multiple ways for our chain-of-thought agent to query the document
  - Basic keyword search
  - Semantic RAG search
  - Figure out how ppl tend to cite the sections, and have a way to query for the text of a specific section, subsection, etc.

- Chain-of-thought Agent to respond to individual comments

  - Need to work with real employees to figure out their goals
    - How are the different ways they respond?
    - How often do responses take one vs many people involved
    - How do you determine which?
    -
  - Identify specific requests in each comment, stripping out filler
  - Identify key phrases
  - Identify referenced sections or quotes from the NPRM
  - Retrieve above referenced information
  - Retrieve any other semantically relevant excerpts (via RAG)

- What's the output? 2 Ideas
  1. A document I prepare and send to them, ideally for a fee
  2. A workspace/tool interface for them to run AI subroutines to help them in responding to a comment
     - Ability to view the original document
     - Scroll through comments
     - View comments in groupings
     - Pull up referenced sections/quotes adjacent to the comments for quick review
