import { describe, expect, it } from 'vitest';
import { mockApi } from '../src/lib/mock';

describe('mock backend plays a hole', () => {
  it('fairway, bunker, mulligan, caddie and holing out', async () => {
    const start = await mockApi.startRound('2026-12-01');
    expect(start.ranked).toBe(true);
    expect(start.page.title).toBe('Octopus');
    const id = start.roundId;

    const fairway = await mockApi.shot(id, {
      shotNo: 1,
      fromIdx: start.page.idx,
      linkTitle: 'Nautilus',
    });
    expect(fairway.lie).toBe('fairway');
    expect(fairway.toPin).toBe(4);

    const bunker = await mockApi.shot(id, {
      shotNo: 2,
      fromIdx: fairway.page.idx,
      linkTitle: 'Cephalopod',
    });
    expect(bunker.lie).toBe('bunker'); // Cephalopod (d5) is farther than Nautilus (d4)

    const back = await mockApi.mulligan(id);
    expect(back.page.title).toBe('Nautilus');

    const cad = await mockApi.caddie(id, ['Cephalopod', 'Jules_Verne']);
    expect(cad.hint).toBe('Jules_Verne'); // Verne (d3) is closer than Nautilus (d4)

    await mockApi.shot(id, { shotNo: 2, fromIdx: back.page.idx, linkTitle: 'Jules_Verne' });
    await mockApi.shot(id, { shotNo: 3, fromIdx: 7, linkTitle: 'Science_fiction' });
    await mockApi.shot(id, { shotNo: 4, fromIdx: 8, linkTitle: 'Moon' });
    const holed = await mockApi.shot(id, { shotNo: 5, fromIdx: 10, linkTitle: 'Apollo_11' });
    expect(holed.holed).toBe(true);
    expect(holed.done).toBe(true);

    const r = await mockApi.result(id);
    expect(r.done).toBe(true);
    expect(r.holed).toBe(true);
    // 5 shots + 1 caddie penalty = 6 on a par 6 -> par.
    expect(r.strokes).toBe(6);
    expect(r.word).toBe('PAR!');
  });
});
