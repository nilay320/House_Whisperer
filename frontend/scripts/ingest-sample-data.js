// Sample data ingestion script for testing
// Run this after setting up your Qdrant Cloud instance

const sampleDocuments = [
  {
    source: "InterNACHI Standards - Electrical Systems",
    section: "Electrical",
    content: `
Electrical System Inspection Standards

1. Service Entrance and Panels
- The inspector shall inspect service drop, service entrance conductors, cables, and raceways
- Service equipment and main disconnects should be properly labeled
- Verify proper grounding and bonding of service equipment
- Check for appropriate clearances around electrical panels (minimum 36 inches in front)
- Panel covers must be in place and secured

2. Branch Circuits, Connected Devices, and Fixtures
- Test all accessible switches, receptacles, and fixtures
- Verify GFCI protection in required locations (bathrooms, kitchens, garages, outdoors)
- Check for proper wire connections and absence of exposed wiring
- Ensure appropriate overcurrent protection for circuits
- Document any aluminum branch circuit wiring

3. Common Defects to Report
- Double-tapped breakers (multiple wires on single breaker)
- Missing knockout covers in panels
- Improper wire splices outside junction boxes
- Reversed polarity at receptacles
- Ungrounded three-prong outlets
    `
  },
  {
    source: "InterNACHI Standards - Plumbing Systems",
    section: "Plumbing",
    content: `
Plumbing System Inspection Standards

1. Water Supply System
- Identify main water shut-off valve location
- Check for functional flow at all fixtures
- Test water pressure (40-80 PSI typical)
- Inspect visible supply piping for leaks, corrosion, or damage
- Note type of supply piping (copper, PEX, galvanized, etc.)

2. Drain, Waste, and Vent Systems
- Test drainage at all fixtures
- Check for proper venting of fixtures
- Inspect visible drain pipes for leaks or damage
- Verify proper slope on horizontal drain lines
- Look for signs of sewer gas odors

3. Water Heating Equipment
- Record type, capacity, and age of water heater
- Check for proper TPR valve and discharge piping
- Verify adequate combustion air for gas units
- Inspect for signs of leaking at tank or connections
- Confirm proper venting of combustion gases
    `
  },
  {
    source: "NCHILB Regulations - Inspector Requirements",
    section: "Licensing",
    content: `
North Carolina Home Inspector Licensure Requirements

1. Education Requirements
- Complete 80 hours of Board-approved pre-licensing education
- Coursework must cover all major home systems
- Include minimum 8 hours of report writing instruction
- Pass the state examination with 70% or higher

2. Experience Requirements  
- Associate License: No experience required, must work under supervision
- Licensed Home Inspector: 100 fee-paid inspections under supervision
- Must complete inspections within 24 months

3. Continuing Education
- 16 hours of continuing education annually
- Must include 4 hours of law and rules update
- Approved courses focus on inspection techniques and standards
- CE must be completed by June 30 each year

4. Standards of Practice
- Follow NC Standards of Practice (based on InterNACHI/ASHI)
- Provide written report within 3 business days
- Maintain errors and omissions insurance
- Disclose any conflicts of interest
    `
  },
  {
    source: "InterNACHI Standards - Roofing Systems",
    section: "Roofing",
    content: `
Roofing System Inspection Standards

1. Roof Covering Materials
- Identify type of roofing material (asphalt, metal, tile, etc.)
- Estimate age and remaining life expectancy
- Look for missing, damaged, or loose materials
- Check for proper installation patterns
- Document any patches or repairs

2. Roof Drainage Systems
- Inspect gutters and downspouts for damage or blockage
- Verify downspouts discharge away from foundation
- Check for proper slope of gutters
- Look for signs of overflow or water damage

3. Flashings and Penetrations
- Inspect flashings at walls, chimneys, and valleys
- Check rubber boots on plumbing vents
- Verify proper sealing around skylights
- Look for rust or deterioration of metal flashings
- Document any signs of water intrusion

4. Limitations
- Not required to walk on roof if unsafe
- May inspect from ground with binoculars
- Not required to determine remaining life
- Report method of inspection used
    `
  }
];

async function ingestData() {
  try {
    const response = await fetch('http://localhost:3000/api/ingest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        documents: sampleDocuments,
        reset: true // This will create a fresh collection
      }),
    });

    const result = await response.json();
    console.log('Ingestion result:', result);
  } catch (error) {
    console.error('Ingestion failed:', error);
  }
}

// Run the ingestion
ingestData();