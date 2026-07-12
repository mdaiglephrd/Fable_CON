// Azure AI Document Intelligence (formerly Form Recognizer) account — used by the
// document-text extraction step (ingest/load_document_text.py consumes its JSONL
// output; the extraction runbook lives in docs/06).
//
// kind 'FormRecognizer' is the single-service Document Intelligence resource.
// Deployed only when deployDocIntel = true in main.bicep.
//
// F0 (free) allows 500 pages/month. The ~24,290-document CON corpus exceeds F0 in
// a single month — plan to batch extraction across months or temporarily scale to
// S0 for the initial backfill, then drop back to F0 (see infra/README.md cost table).

@description('Document Intelligence account name (globally unique; also used as the custom subdomain).')
@minLength(2)
@maxLength(64)
param accountName string

@description('Azure region (must offer Document Intelligence — check regional availability).')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Pricing tier. F0 is the free tier (500 pages/month); S0 is standard pay-as-you-go for backfills that exceed the free monthly limit.')
@allowed(['F0', 'S0'])
param docIntelSku string = 'F0'

resource account 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: {
    name: docIntelSku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // Custom subdomain is required for Entra ID (DefaultAzureCredential / MSI) auth —
    // regional endpoints do not support AAD tokens.
    customSubDomainName: toLower(accountName)
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

@description('Name of the Document Intelligence account.')
output name string = account.name

@description('Document Intelligence endpoint (DOCUMENT_INTELLIGENCE_ENDPOINT).')
output endpoint string = account.properties.endpoint

@description('Principal ID of the Document Intelligence system-assigned identity.')
output principalId string = account.identity.principalId
