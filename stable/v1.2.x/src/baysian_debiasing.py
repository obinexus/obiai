"""
OBINexus Computing: Bayesian Debiasing Framework
Proof of Concept Implementation

This module implements a proof-of-concept for the Bayesian debiasing framework
described in the OBINexus technical paper. It demonstrates the core methodology
for identifying, quantifying, and mitigating bias in a medical diagnostic model.

Author: Nnamdi M. Okpala
Date: April 1, 2025
"""

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import pymc3 as pm
import arviz as az
from sklearn.metrics import confusion_matrix, classification_report

class CausalGraph:
    """
    Directed Acyclic Graph for representing causal relationships between variables.
    
    This class provides methods for constructing, analyzing, and visualizing causal
    relationships, with a specific focus on identifying paths that may introduce bias.
    """
    
    def __init__(self):
        """Initialize an empty causal graph."""
        self.graph = nx.DiGraph()
        
    def add_node(self, node, **attrs):
        """
        Add a node to the graph with optional attributes.
        
        Args:
            node: Node identifier
            **attrs: Node attributes (e.g., 'protected': True)
        """
        self.graph.add_node(node, **attrs)
        
    def add_edge(self, source, target, **attrs):
        """
        Add a directed edge from source to target with optional attributes.
        
        Args:
            source: Source node
            target: Target node
            **attrs: Edge attributes (e.g., 'weight': 0.5)
        """
        self.graph.add_edge(source, target, **attrs)
        
    def get_parents(self, node):
        """
        Get parent nodes of the specified node.
        
        Args:
            node: Node identifier
            
        Returns:
            list: List of parent nodes
        """
        return list(self.graph.predecessors(node))
    
    def get_children(self, node):
        """
        Get child nodes of the specified node.
        
        Args:
            node: Node identifier
            
        Returns:
            list: List of child nodes
        """
        return list(self.graph.successors(node))
    
    def find_paths(self, source, target, exclude_nodes=None):
        """
        Find all paths between source and target nodes.
        
        Args:
            source: Source node
            target: Target node
            exclude_nodes: Nodes to exclude from paths
            
        Returns:
            list: List of paths (each path is a list of nodes)
        """
        exclude_nodes = set() if exclude_nodes is None else set(exclude_nodes)
        
        def find_paths_recursive(current, target, path, visited):
            if current == target:
                return [path + [current]]
                
            if current in visited:
                return []
                
            paths = []
            visited.add(current)
            
            for neighbor in self.graph.successors(current):
                if neighbor not in exclude_nodes:
                    new_paths = find_paths_recursive(neighbor, target, path + [current], visited.copy())
                    paths.extend(new_paths)
                    
            return paths
            
        return find_paths_recursive(source, target, [], set())
    
    def identify_backdoor_paths(self, treatment, outcome, protected_attributes):
        """
        Identify backdoor paths from treatment to outcome through protected attributes.
        
        Args:
            treatment: Treatment variable node
            outcome: Outcome variable node
            protected_attributes: List of protected attribute nodes
            
        Returns:
            list: List of backdoor paths
        """
        backdoor_paths = []
        
        # Check for direct paths from protected attributes to outcome
        for attr in protected_attributes:
            # Find paths from protected attribute to outcome
            attr_to_outcome_paths = self.find_paths(attr, outcome)
            
            # Find paths from protected attribute to treatment
            attr_to_treatment_paths = self.find_paths(attr, treatment)
            
            if attr_to_outcome_paths and attr_to_treatment_paths:
                backdoor_paths.append({
                    'protected_attribute': attr,
                    'paths_to_outcome': attr_to_outcome_paths,
                    'paths_to_treatment': attr_to_treatment_paths
                })
                
        return backdoor_paths
    
    def find_minimal_adjustment_set(self, treatment, outcome, protected_attributes):
        """
        Find the minimal adjustment set to block backdoor paths.
        
        Args:
            treatment: Treatment variable node
            outcome: Outcome variable node
            protected_attributes: List of protected attribute nodes
            
        Returns:
            set: Minimal adjustment set
        """
        # Identify all backdoor paths
        backdoor_paths = self.identify_backdoor_paths(treatment, outcome, protected_attributes)
        
        # Extract all nodes in backdoor paths
        adjustment_candidates = set()
        for path_info in backdoor_paths:
            for path in path_info['paths_to_outcome']:
                adjustment_candidates.update(path)
            for path in path_info['paths_to_treatment']:
                adjustment_candidates.update(path)
        
        # Remove treatment and outcome from candidates
        adjustment_candidates.discard(treatment)
        adjustment_candidates.discard(outcome)
        
        # For simplicity in this PoC, return all candidates
        # In a real implementation, we would use more sophisticated algorithms
        # to find the minimal set
        return adjustment_candidates
    
    def visualize(self, protected_attributes=None, highlight_paths=None, figsize=(10, 8)):
        """
        Visualize the causal graph.
        
        Args:
            protected_attributes: List of protected attribute nodes to highlight
            highlight_paths: List of paths to highlight
            figsize: Figure size as (width, height)
        """
        plt.figure(figsize=figsize)
        
        # Use Kamada-Kawai layout for better node positioning
        pos = nx.kamada_kawai_layout(self.graph)
        
        # Draw nodes
        node_colors = []
        for node in self.graph.nodes():
            if protected_attributes and node in protected_attributes:
                node_colors.append('lightcoral')
            else:
                node_colors.append('lightblue')
                
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, alpha=0.8)
        
        # Draw edges
        edge_colors = []
        for edge in self.graph.edges():
            if highlight_paths and any(edge[0] in path and edge[1] in path for path in highlight_paths):
                edge_colors.append('red')
            else:
                edge_colors.append('black')
                
        nx.draw_networkx_edges(self.graph, pos, edge_color=edge_colors, width=1.0, arrows=True)
        
        # Draw labels
        nx.draw_networkx_labels(self.graph, pos)
        
        plt.title("Causal Graph")
        plt.axis('off')
        plt.tight_layout()
        plt.show()


class BayesianDebiaser:
    """
    Implements the Bayesian debiasing framework for mitigating bias in ML models.
    
    This class provides methods for building a hierarchical Bayesian model that
    explicitly accounts for bias-inducing paths in the causal graph.
    """
    
    def __init__(self, causal_graph, data):
        """
        Initialize the Bayesian debiaser.
        
        Args:
            causal_graph: CausalGraph object representing variable relationships
            data: pandas DataFrame containing the dataset
        """
        self.causal_graph = causal_graph
        self.data = data
        self.model = None
        self.trace = None
        self.bias_variables = None
        
    def identify_bias_nodes(self, target, protected_attributes):
        """
        Identify nodes that introduce bias in predictions.
        
        Args:
            target: Target variable (outcome)
            protected_attributes: List of protected attribute variables
            
        Returns:
            list: Variables that introduce bias
        """
        bias_nodes = set()
        
        # For each protected attribute, find paths to the target
        for attr in protected_attributes:
            # Direct path from protected attribute to target
            paths = self.causal_graph.find_paths(attr, target)
            for path in paths:
                # Add intermediate nodes as bias nodes
                bias_nodes.update(path[1:-1])  # Exclude source and target
                
        self.bias_variables = list(bias_nodes)
        return self.bias_variables
    
    def build_model(self, target, protected_attributes=None):
        """
        Build a hierarchical Bayesian model based on the causal graph.
        
        Args:
            target: Target variable (outcome)
            protected_attributes: List of protected attributes to account for
            
        Returns:
            PyMC3 model
        """
        # Identify bias nodes if protected attributes are provided
        if protected_attributes:
            bias_nodes = self.identify_bias_nodes(target, protected_attributes)
        else:
            bias_nodes = []
            
        with pm.Model() as model:
            # Get all predictors (parents of the target in the causal graph)
            predictors = self.causal_graph.get_parents(target)
            
            # Create variables for each predictor
            vars_dict = {}
            for pred in predictors:
                # If predictor is a bias node, create a hierarchical model
                if pred in bias_nodes:
                    # Group-level effects
                    for attr in protected_attributes:
                        if attr in self.causal_graph.get_parents(pred):
                            # Create hierarchical parameters for each group
                            groups = self.data[attr].unique()
                            n_groups = len(groups)
                            
                            # Group-level intercepts
                            mu = pm.Normal(f'mu_{pred}_{attr}', mu=0, sigma=1)
                            sigma = pm.HalfNormal(f'sigma_{pred}_{attr}', sigma=1)
                            
                            # Group-specific intercepts
                            intercepts = pm.Normal(f'intercepts_{pred}_{attr}', 
                                               mu=mu, 
                                               sigma=sigma, 
                                               shape=n_groups)
                            
                            # Map group indices to data points
                            group_idx = pd.Categorical(self.data[attr]).codes
                            
                            # Apply group-specific intercepts
                            vars_dict[f'{pred}_{attr}_effect'] = intercepts[group_idx]
                
                # Create main effect for the predictor
                if pred in self.data.columns:
                    # Standardize continuous predictors
                    if np.issubdtype(self.data[pred].dtype, np.number):
                        data_std = (self.data[pred] - self.data[pred].mean()) / self.data[pred].std()
                        vars_dict[pred] = pm.Normal(pred, mu=0, sigma=1) * data_std
                    else:
                        # For categorical predictors
                        categories = self.data[pred].unique()
                        n_categories = len(categories)
                        
                        coefs = pm.Normal(f'{pred}_coefs', mu=0, sigma=1, shape=n_categories)
                        cat_idx = pd.Categorical(self.data[pred]).codes
                        vars_dict[pred] = coefs[cat_idx]
            
            # Create the outcome model
            # Combine all predictors and bias effects
            linear_combination = 0
            
            # Add intercept
            intercept = pm.Normal('intercept', mu=0, sigma=1)
            linear_combination += intercept
            
            # Add main effects
            for pred in predictors:
                if pred in vars_dict:
                    linear_combination += vars_dict[pred]
            
            # Add bias effects
            for key, value in vars_dict.items():
                if '_effect' in key:
                    linear_combination += value
            
            # Link function depends on the outcome type
            if np.issubdtype(self.data[target].dtype, np.number):
                # Gaussian likelihood for continuous outcomes
                sigma_y = pm.HalfNormal('sigma_y', sigma=1)
                y = pm.Normal(target, mu=linear_combination, sigma=sigma_y, observed=self.data[target])
            else:
                # Binary outcome
                p = pm.math.sigmoid(linear_combination)
                y = pm.Bernoulli(target, p=p, observed=self.data[target])
            
            self.model = model
            
        return self.model
    
    def fit(self, samples=2000, tune=1000, target_accept=0.8):
        """
        Fit the Bayesian model using MCMC sampling.
        
        Args:
            samples: Number of samples to draw
            tune: Number of tuning steps
            target_accept: Target acceptance rate
            
        Returns:
            Trace of posterior samples
        """
        if self.model is None:
            raise ValueError("Model must be built before fitting")
            
        with self.model:
            self.trace = pm.sample(
                draws=samples,
                tune=tune,
                return_inferencedata=True,
                target_accept=target_accept
            )
            
        return self.trace
    
    def predict(self, new_data, target, bias_correction=True, protected_attributes=None):
        """
        Make predictions using the fitted model.
        
        Args:
            new_data: DataFrame with new data for prediction
            target: Target variable name
            bias_correction: Whether to apply bias correction
            protected_attributes: List of protected attributes to account for
            
        Returns:
            array: Predictions
        """
        if self.trace is None:
            raise ValueError("Model must be fitted before prediction")
            
        # Extract posterior samples
        posterior_samples = self.trace.posterior
        
        # Apply the model to new data
        # This is a simplified version; a full implementation would be more complex
        
        # Get all predictors
        predictors = self.causal_graph.get_parents(target)
        
        # Calculate linear predictor for each sample
        n_samples = len(posterior_samples.chain) * len(posterior_samples.draw)
        linear_preds = np.zeros((n_samples, len(new_data)))
        
        # Add intercept
        intercept = posterior_samples.intercept.values.flatten()
        for i in range(n_samples):
            linear_preds[i, :] = intercept[i]
            
            # Add predictor effects
            for pred in predictors:
                if pred in new_data.columns:
                    # Apply the appropriate transformation based on variable type
                    if np.issubdtype(new_data[pred].dtype, np.number):
                        # Standardize continuous predictors
                        data_std = (new_data[pred] - self.data[pred].mean()) / self.data[pred].std()
                        pred_effect = posterior_samples[pred].values.flatten()[i] * data_std
                    else:
                        # For categorical predictors
                        cat_idx = pd.Categorical(new_data[pred], categories=pd.Categorical(self.data[pred]).categories).codes
                        pred_effect = posterior_samples[f"{pred}_coefs"].values[i, cat_idx]
                    
                    linear_preds[i, :] += pred_effect
            
            # Apply bias correction if requested
            if bias_correction and self.bias_variables and protected_attributes:
                # Zero out bias effects from protected attributes
                for var in self.bias_variables:
                    for attr in protected_attributes:
                        effect_name = f"{var}_{attr}_effect"
                        if effect_name in posterior_samples:
                            # Skip adding the bias effect
                            continue
        
        # Apply link function
        if np.issubdtype(self.data[target].dtype, np.number):
            # Identity link for continuous outcomes
            predictions = linear_preds
        else:
            # Sigmoid link for binary outcomes
            predictions = 1 / (1 + np.exp(-linear_preds))
        
        # Average across posterior samples
        return predictions.mean(axis=0)