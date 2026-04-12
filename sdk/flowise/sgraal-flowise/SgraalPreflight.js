const fetch = require('node-fetch');

class SgraalPreflight {
    constructor() {
        this.label = 'Sgraal Memory Governance';
        this.name = 'sgraalPreflight';
        this.type = 'SgraalPreflight';
        this.category = 'Memory Governance';
        this.description = 'Validate AI agent memory before action';
        this.inputs = [
            { label: 'Memory State', name: 'memoryState', type: 'string' },
            { label: 'Domain', name: 'domain', type: 'string', default: 'general' },
            { label: 'Action Type', name: 'actionType', type: 'string', default: 'reversible' },
            { label: 'API Key', name: 'apiKey', type: 'password' },
        ];
        this.outputs = [{ label: 'Result', name: 'result', type: 'json' }];
    }

    async run(nodeData) {
        const memoryState = JSON.parse(nodeData.inputs.memoryState);
        const resp = await fetch('https://api.sgraal.com/v1/preflight', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${nodeData.inputs.apiKey}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ memory_state: memoryState, domain: nodeData.inputs.domain, action_type: nodeData.inputs.actionType }),
        });
        return await resp.json();
    }
}

module.exports = { nodeClass: SgraalPreflight };
