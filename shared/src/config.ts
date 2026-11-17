/** Shared configuration used by the web app, the Worker and the Python hole builder. */

import config from '../config.json';

export type Wiki = keyof typeof config.wikis;

export const APP_NAME = 'Wiki Golf';
export const APP_VERSION = config.appVersion;
export const REPO_URL = config.repoUrl;
export const CONTACT_EMAIL = config.contactEmail;

/** User-Agent sent on every request to Wikimedia (plan.md hard rule 4). */
export const USER_AGENT = `WikiGolf/${APP_VERSION} (${REPO_URL}; ${CONTACT_EMAIL})`;

/**
 * Launch date. Hole number = days since HOLE_EPOCH + 1.
 * PLACEHOLDER until the owner picks a launch date (see PROGRESS.md open questions).
 */
export const HOLE_EPOCH = config.holeEpoch;

/** Per-wiki settings: language subdomain and title index shard count. */
export const WIKIS = config.wikis;

/** Pages per `snapshots/{snap}/pages/{chunk}.json` file. */
export const PAGE_CHUNK_SIZE = config.pageChunkSize;
