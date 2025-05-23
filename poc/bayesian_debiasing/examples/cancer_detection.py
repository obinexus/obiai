import pandas as pd
import numpy as np
from bayesian_debiasing import CausalGraph, BayesianModel
from bayesian_debiasing.bias_identification import identify_bias_nodes
from bayesian_debiasing.fair_inference import fairness_constrained_inference

# 1. Generate synthetic cancer detection dataset
def generate_biased_cancer_data(n_samples=2000):
    """Generate synthetic cancer detection data with injected bias."""
    # Demographic variables
    age = np.random.normal(50, 15, n_samples)
    gender = np.random.binomial(1, 0.5, n_samples)  # 0=male, 1=female
    ethnicity = np.random.binomial(1, 0.3, n_samples)  # 0=majority, 1=minority
    
    # Risk factors with demographic disparities
    smoking = np.random.binomial(1, 0.3 + 0.1 * (1-ethnicity), n_samples)
    family_history = np.random.binomial(1, 0.2 + 0.05 * age/100, n_samples)
    
    # True cancer status (depends on risk factors but not demographics directly)
    p_cancer = 0.05 + 0.15 * smoking + 0.1 * family_history
    cancer = np.random.binomial(1, p_cancer, n_samples)
    
    # Test results (biased by ethnicity)
    sensitivity = 0.9 - 0.15 * ethnicity  # Lower sensitivity for minorities
    specificity = 0.95 - 0.05 * ethnicity  # Lower specificity for minorities
    
    test_positive = np.zeros(n_samples)
    for i in range(n_samples):
        if cancer[i] == 1:
            test_positive[i] = np.random.binomial(1, sensitivity[i])
        else:
            test_positive[i] = np.random.binomial(1, 1 - specificity[i])
    
    # Create DataFrame
    df = pd.DataFrame({
        'age': age,
        'gender': gender,
        'ethnicity': ethnicity,
        'smoking': smoking,
        'family_history': family_history,
        'cancer': cancer,
        'test_positive': test_positive
    })
    
    return df

# 2. Main execution
def run_cancer_detection_example():
    # Generate data
    data = generate_biased_cancer_data()
    
    # Construct causal graph
    graph = CausalGraph()
    graph.add_edge('ethnicity', 'smoking')
    graph.add_edge('age', 'family_history')
    graph.add_edge('smoking', 'cancer')
    graph.add_edge('family_history', 'cancer')
    graph.add_edge('cancer', 'test_positive')
    graph.add_edge('ethnicity', 'test_positive')  # Bias path
    
    # Identify bias nodes
    protected_attributes = ['ethnicity', 'gender', 'age']
    bias_nodes = identify_bias_nodes(graph, protected_attributes)
    
    # Build and train model
    model = BayesianModel(graph, data)
    model.build_model(bias_nodes=bias_nodes)
    model.estimate_parameters()
    
    # Standard prediction vs fair prediction
    standard_pred = model.predict(data, bias_correction=False)
    fair_pred = model.predict(data, bias_correction=True)
    
    # Evaluate fairness metrics
    from sklearn.metrics import confusion_matrix
    
    def evaluate_by_group(y_true, y_pred, group):
        groups = data[group].unique()
        results = {}
        
        for g in groups:
            mask = data[group] == g
            cm = confusion_matrix(y_true[mask], y_pred[mask])
            tn, fp, fn, tp = cm.ravel()
            
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
            
            results[g] = {
                'sensitivity': sensitivity,
                'specificity': specificity,
                'ppv': ppv
            }
        
        return results
    
    # Evaluate standard predictions
    standard_metrics = evaluate_by_group(data['cancer'], standard_pred > 0.5, 'ethnicity')
    
    # Evaluate fair predictions
    fair_metrics = evaluate_by_group(data['cancer'], fair_pred > 0.5, 'ethnicity')
    
    # Print results
    print("Standard Model Performance by Ethnicity:")
    print(standard_metrics)
    print("\nFair Model Performance by Ethnicity:")
    print(fair_metrics)
    
    # Visualize results
    # (Visualization code here)

if __name__ == "__main__":
    run_cancer_detection_example()