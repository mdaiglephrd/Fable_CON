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
// NOTE on identity: an earlier version of this module declared a system-assigned
// identity here for forward-compatibility (it was granted no data-plane RBAC).
// That combination -- sku Free + a declared identity block -- fails ARM
// deployment-time validation with "SkuCode 'Free' is invalid", a known Bicep/ARM
// quirk (see Azure/static-web-apps#384, #571) rather than a real product
// restriction. Since nothing consumed the identity, it's removed here rather
// than worked around. At Free tier the console just calls the FastAPI backend
// over HTTPS, so no identity is needed today; add it back (Standard tier only,
// per Microsoft docs, if it's ever needed for Key Vault references) if a real
// consumer shows up.

@description('Static Web App name (globally unique).')
param staticWebAppName string

@description('Azure region. Static Web Apps are offered in a limited set of regions (e.g. westus2, centralus, eastus2, westeurope, eastasia) — override via main.bicep if the resource group region is unsupported.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {  
  name: staticWebAppName
  location: location
  tags: tags
  sku: {
    name: 'Free'
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
