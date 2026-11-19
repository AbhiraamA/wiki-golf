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

/**
 * True until a real launch date is set. While true, the UI hides the (meaningless) hole number
 * and shows the weekday + date instead. Flip to false in config.json at launch, together with a
 * real HOLE_EPOCH.
 */
export const HOLE_EPOCH_PLACEHOLDER: boolean = config.holeEpochPlaceholder;

/** Per-wiki settings: language subdomain and title index shard count. */
export const WIKIS = config.wikis;

/** Pages per `snapshots/{snap}/pages/{chunk}.json` file. */
export const PAGE_CHUNK_SIZE = config.pageChunkSize;
