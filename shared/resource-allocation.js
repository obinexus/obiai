/**
 * OBINexus Resource Allocation Algorithm
 * 
 * This algorithm implements a systematic approach to resource allocation
 * across both the Unbiased Medical AI and OBI Heart AI projects,
 * accounting for dependencies, priority shifts, and technical requirements.
 */

// Phase definitions with resource requirements and dependencies
const phases = {
  // Unbiased Medical AI phases
  unbiasedPhase1: {
    name: "Mathematical Formulation",
    resourceUnits: 40,
    duration: 30, // days
    dependencies: [],
    priority: 0.9
  },
  unbiasedPhase2: {
    name: "Sampling Algorithm Development",
    resourceUnits: 50,
    duration: 45,
    dependencies: ["unbiasedPhase1"],
    priority: 0.85
  },
  unbiasedPhase3: {
    name: "Model Validation Suite",
    resourceUnits: 35,
    duration: 30,
    dependencies: ["unbiasedPhase2"],
    priority: 0.8
  },
  unbiasedPhase4: {
    name: "ML Pipeline Integration",
    resourceUnits: 25,
    duration: 20,
    dependencies: ["unbiasedPhase3"],
    priority: 0.75
  },
  unbiasedPhase5: {
    name: "Deployment & Monitoring",
    resourceUnits: 30,
    duration: 25,
    dependencies: ["unbiasedPhase4"],
    priority: 0.7
  },
  
  // OBI Heart AI phases
  obiPhase1: {
    name: "Requirements Analysis",
    resourceUnits: 30,
    duration: 25,
    dependencies: [],
    priority: 0.8
  },
  obiPhase2: {
    name: "Core Engine Development",
    resourceUnits: 60,
    duration: 50,
    dependencies: ["obiPhase1", "unbiasedPhase1"],
    priority: 0.85
  },
  obiPhase3: {
    name: "Integration Testing",
    resourceUnits: 40,
    duration: 30,
    dependencies: ["obiPhase2"],
    priority: 0.8
  },
  obiPhase4: {
    name: "Performance Optimization",
    resourceUnits: 45,
    duration: 35,
    dependencies: ["obiPhase3", "unbiasedPhase3"],
    priority: 0.75
  },
  obiPhase5: {
    name: "Production Deployment",
    resourceUnits: 30,
    duration: 25,
    dependencies: ["obiPhase4"],
    priority: 0.7
  }
};

/**
 * Resource allocation algorithm that determines optimal distribution
 * based on dependencies, priorities, and available resources
 * 
 * @param {Object} phases - The phase definitions
 * @param {Number} availableResources - Total resource units available
 * @returns {Object} Allocation plan with schedule and resource distribution
 */
function allocateResources(phases, availableResources) {
  // Initialize tracking variables
  const schedule = {};
  const completedPhases = new Set();
  const activePhases = new Set();
  let currentDay = 0;
  const allocationHistory = [];
  
  // Continue until all phases are completed
  while (completedPhases.size < Object.keys(phases).length) {
    // Find eligible phases (dependencies satisfied)
    const eligiblePhases = Object.keys(phases).filter(phaseId => {
      if (completedPhases.has(phaseId) || activePhases.has(phaseId)) {
        return false;
      }
      
      // Check if all dependencies are satisfied
      return phases[phaseId].dependencies.every(dep => completedPhases.has(dep));
    });
    
    // Sort eligible phases by priority
    eligiblePhases.sort((a, b) => phases[b].priority - phases[a].priority);
    
    // Allocate resources to active and new phases
    let remainingResources = availableResources;
    
    // First allocate to active phases
    activePhases.forEach(phaseId => {
      const phase = phases[phaseId];
      const requiredResources = Math.min(phase.resourceUnits, remainingResources);
      remainingResources -= requiredResources;
      
      // Update phase progress
      if (!schedule[phaseId]) {
        schedule[phaseId] = {
          startDay: currentDay,
          allocatedDays: 0,
          remainingDays: phase.duration
        };
      }
      
      schedule[phaseId].allocatedDays += 1;
      schedule[phaseId].remainingDays -= 1;
      
      // Check if phase is completed
      if (schedule[phaseId].remainingDays <= 0) {
        activePhases.delete(phaseId);
        completedPhases.add(phaseId);
        schedule[phaseId].endDay = currentDay;
      }
    });
    
    // Allocate remaining resources to new eligible phases
    for (const phaseId of eligiblePhases) {
      if (remainingResources <= 0) break;
      
      const phase = phases[phaseId];
      const requiredResources = Math.min(phase.resourceUnits, remainingResources);
      
      if (requiredResources > 0) {
        remainingResources -= requiredResources;
        activePhases.add(phaseId);
        
        schedule[phaseId] = {
          startDay: currentDay,
          allocatedDays: 1,
          remainingDays: phase.duration - 1
        };
        
        // Check if phase is completed in one day (unlikely but possible)
        if (schedule[phaseId].remainingDays <= 0) {
          activePhases.delete(phaseId);
          completedPhases.add(phaseId);
          schedule[phaseId].endDay = currentDay;
        }
      }
    }
    
    // Record allocation for this day
    allocationHistory.push({
      day: currentDay,
      activePhases: Array.from(activePhases),
      completedPhases: Array.from(completedPhases),
      remainingResources
    });
    
    // Move to next day
    currentDay++;
  }
  
  return {
    schedule,
    totalDuration: currentDay,
    allocationHistory
  };
}

/**
 * Generate a table representation of the resource allocation plan
 * 
 * @param {Object} allocationPlan - The allocation plan from allocateResources
 * @param {Object} phases - The phase definitions
 * @returns {String} Text representation of the allocation plan
 */
function generateResourcePlan(allocationPlan, phases) {
  const { schedule, totalDuration } = allocationPlan;
  
  let output = "OBINexus Resource Allocation Plan\n";
  output += "=====================================\n\n";
  
  output += "Project Timeline: " + totalDuration + " days\n\n";
  
  output += "Phase Schedule:\n";
  output += "-------------\n";
  
  // Group phases by project
  const unbiasedPhases = Object.keys(schedule).filter(id => id.startsWith("unbiased"));
  const obiPhases = Object.keys(schedule).filter(id => id.startsWith("obi"));
  
  output += "\nUnbiased Medical AI Track:\n";
  unbiasedPhases.forEach(phaseId => {
    const phase = phases[phaseId];
    const details = schedule[phaseId];
    output += `  ${phase.name}: Days ${details.startDay} - ${details.endDay} (${phase.duration} days)\n`;
  });
  
  output += "\nOBI Heart AI Track:\n";
  obiPhases.forEach(phaseId => {
    const phase = phases[phaseId];
    const details = schedule[phaseId];
    output += `  ${phase.name}: Days ${details.startDay} - ${details.endDay} (${phase.duration} days)\n`;
  });
  
  output += "\nCritical Dependencies:\n";
  output += "---------------------\n";
  Object.keys(phases).forEach(phaseId => {
    const phase = phases[phaseId];
    if (phase.dependencies.length > 0) {
      output += `  ${phase.name} depends on: ${phase.dependencies.map(dep => phases[dep].name).join(", ")}\n`;
    }
  });
  
  return output;
}

// Decision points for conditional progression
function evaluateDecisionPoints(allocationPlan, phases) {
  const decisionPoints = [];
  
  Object.keys(allocationPlan.schedule).forEach(phaseId => {
    const phase = phases[phaseId];
    const schedule = allocationPlan.schedule[phaseId];
    
    // Decision point at phase completion
    decisionPoints.push({
      day: schedule.endDay,
      phase: phase.name,
      decision: `IF ${phase.name} meets quality criteria THEN proceed to next dependency phase`,
      alternativeAction: `IF quality issues found THEN allocate additional resources to resolve before proceeding`
    });
    
    // Mid-phase checkpoint for longer phases
    if (phase.duration > 30) {
      const checkpointDay = schedule.startDay + Math.floor(phase.duration / 2);
      decisionPoints.push({
        day: checkpointDay,
        phase: phase.name,
        decision: `IF ${phase.name} progress on track THEN continue as planned`,
        alternativeAction: `IF progress below 50% completion THEN evaluate resource allocation and technical blockers`
      });
    }
  });
  
  return decisionPoints.sort((a, b) => a.day - b.day);
}

// This function would be used in a real implementation to dynamically
// adjust resource allocation based on progress and technical dependencies.

// Main function to execute the resource allocation process
function main() {
  const availableResources = 100; // Arbitrary resource units
  const allocationPlan = allocateResources(phases, availableResources);
  const planSummary = generateResourcePlan(allocationPlan, phases);
  
  console.log(planSummary);

  const decisionPoints = evaluateDecisionPoints(allocationPlan, phases);
  console.log("\nDecision Points:");
  decisionPoints.forEach(dp => {
    console.log(`Day ${dp.day}: ${dp.decision}`);
    console.log(`  Alternative: ${dp.alternativeAction}`);
  });
}

// Execute the main function
main();

