/** Shared configuration used by the web app and the Worker. */

export const APP_NAME = 'Wiki Golf';
export const APP_VERSION = '0.0.0';
export const REPO_URL = 'https://github.com/AbhiraamA/wiki-golf';
export const CONTACT_EMAIL = 'wikigolf23@gmail.com';

/** User-Agent sent on every request to Wikimedia (plan.md hard rule 4). */
export const USER_AGENT = `WikiGolf/${APP_VERSION} (${REPO_URL}; ${CONTACT_EMAIL})`;

/**
 * Launch date. Hole number = days since HOLE_EPOCH + 1.
 * PLACEHOLDER until the owner picks a launch date (see PROGRESS.md open questions).
 */
export const HOLE_EPOCH = '2026-12-01';

export type Wiki = 'simplewiki' | 'enwiki';
