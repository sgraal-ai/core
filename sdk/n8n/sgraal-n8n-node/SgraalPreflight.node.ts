import { IExecuteFunctions, INodeExecutionData, INodeType, INodeTypeDescription } from 'n8n-workflow';

export class SgraalPreflight implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Sgraal Memory Governance',
    name: 'sgraalPreflight',
    group: ['transform'],
    version: 1,
    description: 'Validate AI agent memory before action with Sgraal preflight',
    defaults: { name: 'Sgraal Preflight' },
    inputs: ['main'],
    outputs: ['main', 'main'],
    outputNames: ['continue', 'blocked'],
    credentials: [{ name: 'sgraalApi', required: true }],
    properties: [
      {
        displayName: 'Operation',
        name: 'operation',
        type: 'options',
        options: [
          { name: 'Preflight', value: 'preflight' },
          { name: 'Batch', value: 'batch' },
          { name: 'Heal', value: 'heal' },
          { name: 'Explain', value: 'explain' },
        ],
        default: 'preflight',
      },
      {
        displayName: 'Memory State',
        name: 'memoryState',
        type: 'json',
        default: '[]',
        description: 'JSON array of memory entries in MemCube format',
      },
      {
        displayName: 'Domain',
        name: 'domain',
        type: 'options',
        options: [
          { name: 'General', value: 'general' },
          { name: 'Fintech', value: 'fintech' },
          { name: 'Medical', value: 'medical' },
          { name: 'Legal', value: 'legal' },
          { name: 'Coding', value: 'coding' },
          { name: 'Customer Support', value: 'customer_support' },
        ],
        default: 'general',
      },
      {
        displayName: 'Action Type',
        name: 'actionType',
        type: 'options',
        options: [
          { name: 'Informational', value: 'informational' },
          { name: 'Reversible', value: 'reversible' },
          { name: 'Irreversible', value: 'irreversible' },
          { name: 'Destructive', value: 'destructive' },
        ],
        default: 'reversible',
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const credentials = await this.getCredentials('sgraalApi');
    const memoryState = JSON.parse(this.getNodeParameter('memoryState', 0) as string);
    const domain = this.getNodeParameter('domain', 0) as string;
    const actionType = this.getNodeParameter('actionType', 0) as string;

    const response = await this.helpers.httpRequest({
      method: 'POST',
      url: 'https://api.sgraal.com/v1/preflight',
      headers: {
        'Authorization': `Bearer ${credentials.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: { memory_state: memoryState, domain, action_type: actionType },
    });

    const decision = response.recommended_action;
    const output: INodeExecutionData = { json: response };

    if (decision === 'BLOCK') {
      return [[], [output]]; // blocked branch
    }
    return [[output], []]; // continue branch
  }
}
