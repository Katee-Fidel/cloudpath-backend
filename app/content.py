# Original teaching questions. These are not exam items or exam simulations.
TOPICS = {
    "cloud": {"name": "Cloud concepts", "weight": 0.275, "range": "25–30%"},
    "services": {"name": "Azure architecture and services", "weight": 0.375, "range": "35–40%"},
    "governance": {"name": "Azure management and governance", "weight": 0.35, "range": "30–35%"},
}
BANK = {
"cloud": [
("A Nairobi delivery app needs extra capacity during a weekend sale, then less on Monday. Which benefit fits?", ["Elasticity", "Fixed capacity", "Physical ownership", "Manual procurement"], 0, "Elasticity adjusts resources as demand rises and falls. Fixed capacity and buying hardware cannot respond as quickly; manual procurement adds delay."),
("A co-op rents virtual machines. Who normally patches the guest operating system?", ["The customer", "The electricity provider", "Only Microsoft", "No one"], 0, "With IaaS virtual machines, the customer manages the guest OS. The cloud provider manages the physical infrastructure. The power provider and 'no one' do not satisfy this responsibility."),
("A small shop uses a complete hosted email application. Which service model is this?", ["IaaS", "SaaS", "PaaS", "On-premises hardware"], 1, "SaaS provides a ready-to-use application. IaaS provides infrastructure; PaaS provides a development platform; on-premises hardware is owned or managed locally."),
("A retailer keeps one system in its datacenter and connects it to a public cloud. Which model describes this?", ["Private only", "Hybrid cloud", "Public only", "Offline computing"], 1, "Hybrid cloud combines private or on-premises infrastructure with public cloud resources. Public-only and private-only models omit one side; offline computing has no such connection."),
],
"services": [
("A farmers’ co-op stores photos of produce for its website. Which service suits object storage?", ["Azure Blob Storage", "Azure DNS", "Azure Policy", "Azure Virtual Network"], 0, "Blob Storage holds unstructured objects such as photos. DNS resolves names, Policy enforces governance rules, and a virtual network connects resources."),
("A logistics team wants isolation from a single datacenter failure within one supported region. What should it consider?", ["Availability zones", "Resource tags", "One VM only", "A naming convention"], 0, "Availability zones are physically separate locations within a region. A suitable deployment across zones can improve availability. Tags and names organise resources; a single VM offers no zone redundancy."),
("A developer needs permission to read, but not change, Azure resources. Which mechanism assigns that access?", ["Storage tiers", "Azure RBAC", "DNS records", "Cost tags"], 1, "Azure role-based access control assigns permissions at a scope. Storage tiers manage access cost, DNS resolves names, and tags classify resources; none assigns resource access permissions."),
("A regional distributor connects Azure resources using private IP addresses. What is the network foundation?", ["Azure Virtual Network", "Azure Advisor", "Microsoft Purview", "Resource locks"], 0, "A virtual network enables private networking. Advisor recommends improvements, Purview supports data governance, and locks guard against resource changes."),
],
"governance": [
("A county IT team wants to restrict new deployments to approved Azure regions. Which tool fits?", ["Azure Policy", "Azure DNS", "Blob Storage", "Application Insights"], 0, "Azure Policy evaluates and can enforce resource rules such as allowed locations. DNS handles naming, Blob stores objects, and Application Insights monitors applications."),
("A co-op wants to group cloud spending by department without moving resources. What should it apply?", ["Tags", "New passwords", "Availability zones", "VPN tunnels"], 0, "Tags attach metadata used for organising and analysing costs. Passwords control authentication, zones address resilience, and VPNs connect networks."),
("An operator wants to protect a resource from accidental deletion. Which feature fits?", ["A delete lock", "A DNS record", "A storage tier", "A larger VM"], 0, "A delete lock prevents deletion until removed by an authorised identity. DNS, storage tiers, and VM sizing do not prevent deletion. Locks are not a substitute for access control."),
("A developer needs application telemetry and request-failure analysis. Which Azure Monitor capability fits?", ["Application Insights", "Resource groups alone", "Tags alone", "Pricing calculator"], 0, "Application Insights provides application performance monitoring and telemetry. Resource groups organise resources, tags label them, and the pricing calculator estimates costs."),
]}

def questions(topic, count):
    return [{"question": q, "options": o, "answer": a, "explanation": e} for q,o,a,e in BANK[topic][:count]]
