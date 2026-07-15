# EverReal QA — Test Project

Playwright + TypeScript QA project for the EverReal Property Portal Lite
(`https://qa-darshan.vercel.app`).

## Setup

```bash
npm install
npx playwright install chromium
cp .env.example .env   # fill in ALPEN_AGENT_EMAIL / ALPEN_AGENT_PASSWORD
npx playwright test tests/auth/auth.setup.ts   # generates fixtures/*.json
```

## Risk Charter
Feature: Tenant data isolation

  Scenario: An agent cannot read another agency's contact
    Given I am logged in as an agent of "Alpen" agency
    And a contact with id 1 belongs to the "EverReal" agency
    When I request GET /contacts/1
    Then the response must not contain that contact's data
    And the response status must be 403 or 404

## Exploratory Notes

## Bug Reports

## Automation

## AI Artifact

## Go/No-Go
