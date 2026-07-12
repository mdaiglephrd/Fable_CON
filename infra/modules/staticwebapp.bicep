// Azure Static Web App (Free plan) for the React research console in web/.
//
// The console is deployed to this resource out-of-band (SWA CLI / GitHub Actions /
// `az staticwebapp` — see infra/README.md), NOT from Bicep: there is no repo
// linkage here (no repositoryUrl/token), so the app stays deployment-source
// agnostic and no GitHub PAT is required in the template.
//
// App settings, the API/backend linkage and the Entra ID auth registration are
// configured via web/staticwebapp.config.json and the SWA portal/CLI — the Free
// plan supports Microsoft Entra ID authentication. This module intentionally
// provisions only the hosting resource + identity.
//
// NOTE on identity: ARM accepts a system-assigned identity on the Free plan, but
// *using* that identity for Key Vault references (keyVaultReferenceIdentity) needs
// the Standard plan (per Microsoft docs). At Free tier the console just calls the
// FastAPI backend over HTTPS, so the identity is declared for forward-compatibility
// and is granted no data-plane RBAC (see main.bicep / roles*.bicep).

@description('Static Web App name (globally unique).')
param staticWebAppName string

@description('Azure region. Static Web Apps are offered in a limited set of regions (e.g. westus2, centralus, eastus2, westeurope, eastasia) — override via main.bicep if the resource group region is unsupported.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Static Web Apps hosting plan. Free is the default; Standard adds SLA, private endpoints, custom auth registrations and Key Vault reference support.')
@allowed(['Free', 'Standard'])
param sku string = 'Free'

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // Deployment source (repo/branch) is left unset: the console is published via
    // the SWA CLI / az staticwebapp / GitHub Actions post-deploy, not from Bicep.
    allowConfigFileUpdates: true
    stagingEnvironmentPolicy: 'Enabled'
    publicNetworkAccess: 'Enabled'
  }
}

@description('Name of the Static Web App resource.')
output name string = staticWebApp.name

@description('Default *.azurestaticapps.net hostname for the console (CONSOLE_ORIGIN host).')
output defaultHostName string = staticWebApp.properties.defaultHostname

@description('Principal ID of the Static Web App system-assigned identity.')
output principalId string = staticWebApp.identity.principalId
