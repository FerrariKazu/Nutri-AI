/**
 * UniProtClient.js
 * 
 * ARCHITECTURAL ISOLATION RULE:
 * This client provides EXTERNAL annotations only.
 * It is NOT permitted to influence core trace metrics or epistemic status.
 */

const UNIPROT_CACHE_KEY = 'nutri_uniprot_cache_v1';

class UniProtClient {
    constructor() {
        this.cache = this._loadCache();
    }

    _loadCache() {
        const raw = localStorage.getItem(UNIPROT_CACHE_KEY);
        try {
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            return {};
        }
    }

    _saveCache() {
        localStorage.setItem(UNIPROT_CACHE_KEY, JSON.stringify(this.cache));
    }

    async getProteinAnnotation(uniprotId) {
        if (!uniprotId) return null;

        // 1. Check Cache
        if (this.cache[uniprotId]) {
            return this.cache[uniprotId];
        }

        // 2. Fetch from UniProt
        try {
            console.log(`🧬 [UNIPROT_ISOLATION] Fetching external annotation for ${uniprotId}`);
            const response = await fetch(`https://rest.uniprot.org/uniprotkb/${uniprotId}.json`);

            if (!response.ok) throw new Error(`UniProt API Error: ${response.status}`);

            const data = await response.json();

            // 3. Extract relevant (non-epistemic) metadata
            const annotation = {
                id: uniprotId,
                name: data.proteinDescription?.recommendedName?.fullName?.value || uniprotId,
                gene: data.genes?.[0]?.geneName?.value || 'N/A',
                organism: data.organism?.scientificName || 'Homo sapiens',
                function: data.comments?.find(c => c.commentType === 'FUNCTION')?.texts?.[0]?.value || 'Functional data unavailable in UniProt snapshot.',
                fetchedAt: new Date().toISOString(),
                source: 'UniProt KB (External)'
            };

            // 4. Update Cache
            this.cache[uniprotId] = annotation;
            this._saveCache();

            return annotation;
        } catch (error) {
            console.error(`🧬 [UNIPROT_ISOLATION] Failed to fetch external data: ${error.message}`);
            return {
                id: uniprotId,
                error: true,
                message: "External annotation service unreachable."
            };
        }
    }
}

export const uniprotClient = new UniProtClient();
