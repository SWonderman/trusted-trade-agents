import type { OrderStatus, PolicyOutcome, ReasonSeverity } from '#lib/api/types.js';

const eur = new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR' });
const eurWhole = new Intl.NumberFormat('en-IE', {
	style: 'currency',
	currency: 'EUR',
	maximumFractionDigits: 0
});
const num = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });

export const money = (v: number) => eur.format(v);
export const moneyWhole = (v: number) => eurWhole.format(v);
export const number = (v: number) => num.format(v);
export const percent = (v: number) => `${Math.round(v * 100)}%`;

export function date(iso: string) {
	return new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso).toLocaleDateString('en-GB', {
		weekday: 'short',
		day: 'numeric',
		month: 'short',
		timeZone: 'Europe/Helsinki'
	});
}

export function dateTime(iso: string) {
	return new Date(iso).toLocaleString('en-GB', {
		day: 'numeric',
		month: 'short',
		hour: '2-digit',
		minute: '2-digit',
		timeZone: 'Europe/Helsinki'
	});
}

export function time(iso: string) {
	return new Date(iso).toLocaleTimeString('en-GB', {
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
		timeZone: 'Europe/Helsinki'
	});
}

export function relative(iso: string, now = Date.now()) {
	const s = Math.round((now - new Date(iso).getTime()) / 1000);
	const future = s < 0;
	const a = Math.abs(s);
	const v =
		a < 60
			? `${a}s`
			: a < 3600
				? `${Math.round(a / 60)} min`
				: a < 86400
					? `${Math.round(a / 3600)} h`
					: `${Math.round(a / 86400)} d`;
	return future ? `in ${v}` : `${v} ago`;
}

export const outcomeLabel: Record<ReasonSeverity, string> = {
	AUTO_APPROVE: 'Auto-approved',
	NEEDS_HUMAN: 'Needs approval',
	REJECT: 'Rejected by policy',
	INFO: 'For information'
};

export const statusLabel: Record<OrderStatus, string> = {
	PENDING_APPROVAL: 'Waiting for approval',
	CONFIRMED: 'Confirmed',
	APPROVED: 'Approved',
	PLACED: 'Placed',
	REJECTED: 'Rejected'
};

export const statusTone: Record<OrderStatus, PolicyOutcome | 'neutral'> = {
	PENDING_APPROVAL: 'NEEDS_HUMAN',
	CONFIRMED: 'AUTO_APPROVE',
	APPROVED: 'AUTO_APPROVE',
	PLACED: 'AUTO_APPROVE',
	REJECTED: 'REJECT'
};

/** Human names for the GS1 / unit codes the UI shows. */
export const unitName: Record<string, string> = {
	KI: 'case',
	ST: 'piece',
	PAK: 'pack',
	KG: 'kg',
	L: 'litre'
};

export function claimText(c: { type: string; element: string }) {
	return `${c.type}_${c.element}`;
}
