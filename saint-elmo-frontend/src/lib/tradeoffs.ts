import type { OrderLine, PolicyReason, ProductFacts } from '#lib/api/types.js';
import { claimText, daysLate } from '#lib/format.js';

/** A substitute line against the product it replaces. */
export interface SubstituteTradeOffs {
	/** The original's name, from its line on the order or the catalog. */
	originalName: string | null;
	/** The policy's reasons on the substitute line: a price rise, a missing claim, lateness… */
	reasons: PolicyReason[];
	/** Price per litre or kilo against the original's, in percent, when both are on the order. */
	pricePerUnitDeltaPct: number | null;
	/** Days the substitute arrives after the original, when both are on the order. */
	daysLater: number | null;
	/** From the catalog, when it has both products; null otherwise. */
	declared: {
		lost: string[];
		gained: string[];
		/** Set when the vendor changes. */
		vendors: { original: string; substitute: string } | null;
	} | null;
}

const declarations = (p: ProductFacts) => [...p.claims.map(claimText), ...p.diets, ...p.labels];

/**
 * What a substitute gives up and gains. The order's own data comes first: the line's
 * reasons, and its offer against the original's when the order has a line for that too
 * (a partial fill). The catalog adds declared claims, diets and labels when it has both.
 */
export function substituteTradeOffs(
	line: OrderLine,
	lines: OrderLine[],
	products: Record<string, ProductFacts>
): SubstituteTradeOffs | null {
	if (!line.substitutesFor) return null;
	const original = lines.find((l) => l.productCode === line.substitutesFor);

	const price = line.price?.comparisonPrice;
	const originalPrice = original?.price?.comparisonPrice;
	const comparable = price && originalPrice && price.unit === originalPrice.unit;
	const earliest = line.availability?.earliestDate;
	const originalEarliest = original?.availability?.earliestDate;

	const product = products[line.productCode];
	const originalProduct = products[line.substitutesFor];
	let declared: SubstituteTradeOffs['declared'] = null;
	if (product && originalProduct) {
		const has = declarations(product);
		const had = declarations(originalProduct);
		declared = {
			lost: had.filter((d) => !has.includes(d)),
			gained: has.filter((d) => !had.includes(d)),
			vendors:
				product.vendor !== originalProduct.vendor
					? { original: originalProduct.vendor, substitute: product.vendor }
					: null
		};
	}

	return {
		originalName: original?.name ?? originalProduct?.name ?? null,
		reasons: line.reasons.filter((r) => r.severity !== 'INFO'),
		pricePerUnitDeltaPct: comparable
			? Math.round(((price.value - originalPrice.value) / originalPrice.value) * 1000) / 10
			: null,
		daysLater: earliest && originalEarliest ? daysLate(earliest, originalEarliest) : null,
		declared
	};
}
