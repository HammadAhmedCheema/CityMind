"""
ch5_crime.py - Challenge 5: Crime Risk Prediction.

Step 1: K-Means Clustering (unsupervised) - group neighborhoods by density & industrial proximity.
Step 2: Synthetic crime data generation based on cluster properties.
Step 3: KNN Classification (supervised) - predict High/Medium/Low risk.

All algorithms are implemented from scratch. Only numpy is used for array operations.
"""

import random
import numpy as np
import config as cfg


def predict_crime(graph):
    """
    Full crime prediction pipeline:
    1. K-Means clustering on node features
    2. Generate synthetic crime data
    3. KNN classification to predict risk labels
    4. Feed risk labels back into the graph as cost multipliers
    """
    graph.log("Ch5: Starting crime prediction pipeline")

    # -- Step 0: Extract features from each node --------------
    positions = []
    features = []  # [population_density, industrial_proximity]

    industrial_positions = graph.get_nodes_by_type("industrial")

    for r in range(graph.rows):
        for c in range(graph.cols):
            pos = (r, c)
            node = graph.nodes[pos]
            positions.append(pos)

            # Industrial proximity: inverse of min Manhattan distance to any industrial zone
            if industrial_positions:
                min_dist = min(abs(r - ir) + abs(c - ic) for ir, ic in industrial_positions)
                industrial_prox = 1.0 / (1.0 + min_dist)  # normalize to (0, 1]
            else:
                industrial_prox = 0.0

            features.append([node.population_density, industrial_prox])

    X = np.array(features)

    # -- Step 1: K-Means Clustering ---------------------------
    graph.log(f"Ch5: Running K-Means (K={cfg.KMEANS_K})")
    cluster_labels = k_means(X, cfg.KMEANS_K)

    # -- Step 2: Generate synthetic crime data ---------------─
    graph.log("Ch5: Generating synthetic crime dataset")
    crime_rates = _generate_crime_data(X, cluster_labels)

    # Assign labels: High (top 33%), Medium (mid 33%), Low (bottom 33%)
    sorted_rates = sorted(crime_rates)
    n = len(sorted_rates)
    low_threshold = sorted_rates[n // 3]
    high_threshold = sorted_rates[2 * n // 3]

    crime_labels = []
    for rate in crime_rates:
        if rate >= high_threshold:
            crime_labels.append("High")
        elif rate >= low_threshold:
            crime_labels.append("Medium")
        else:
            crime_labels.append("Low")

    # -- Step 3: KNN Classification ---------------------------
    # Build feature matrix with cluster labels for supervised learning
    X_supervised = np.column_stack([X, cluster_labels])

    graph.log(f"Ch5: Running KNN classification (K={cfg.KNN_K})")
    predicted_labels = knn_classify(X_supervised, crime_labels, cfg.KNN_K)

    # -- Step 4: Feed back into graph ------------------------─
    for i, pos in enumerate(positions):
        graph.nodes[pos].crime_risk = predicted_labels[i]
        graph.nodes[pos].risk_index = crime_rates[i]

    # Update edge costs with crime risk multipliers
    _apply_risk_to_edges(graph)

    # Count risk distribution
    risk_counts = {"High": 0, "Medium": 0, "Low": 0}
    for label in predicted_labels:
        risk_counts[label] += 1

    graph.log(f"Ch5: Risk distribution - High: {risk_counts['High']}, "
              f"Medium: {risk_counts['Medium']}, Low: {risk_counts['Low']}")


# ===============================================================
# K-MEANS CLUSTERING (hand-written)
# ===============================================================

def k_means(X, k):
    """
    K-Means clustering algorithm.

    Steps:
    1. Initialize k centroids randomly from the data points
    2. Assign each point to the nearest centroid (Euclidean distance)
    3. Recompute centroids as the mean of assigned points
    4. Repeat until centroids converge (shift < tolerance) or max iterations

    Args:
        X: numpy array of shape (n_samples, n_features)
        k: number of clusters

    Returns:
        labels: numpy array of shape (n_samples,) - cluster index for each point
    """
    n_samples, n_features = X.shape

    # Step 1: Random initialization - pick k distinct data points
    indices = random.sample(range(n_samples), k)
    centroids = X[indices].copy()

    labels = np.zeros(n_samples, dtype=int)

    for iteration in range(cfg.KMEANS_MAX_ITER):
        # Step 2: Assign each point to nearest centroid
        for i in range(n_samples):
            distances = np.array([_euclidean_distance(X[i], centroids[j])
                                  for j in range(k)])
            labels[i] = np.argmin(distances)

        # Step 3: Recompute centroids
        new_centroids = np.zeros_like(centroids)
        for j in range(k):
            cluster_points = X[labels == j]
            if len(cluster_points) > 0:
                new_centroids[j] = cluster_points.mean(axis=0)
            else:
                # Empty cluster - reinitialize randomly
                new_centroids[j] = X[random.randint(0, n_samples - 1)]

        # Step 4: Check convergence
        centroid_shift = sum(_euclidean_distance(centroids[j], new_centroids[j])
                            for j in range(k))

        centroids = new_centroids

        if centroid_shift < cfg.KMEANS_TOL:
            break

    return labels


# ===============================================================
# KNN CLASSIFICATION (hand-written)
# ===============================================================

def knn_classify(X, labels, k):
    """
    K-Nearest Neighbors classification using leave-one-out on training data.

    For each data point, find the k nearest OTHER points (by Euclidean distance)
    and predict the majority class.

    Args:
        X: numpy array of shape (n_samples, n_features)
        labels: list of string labels (same length as X)
        k: number of neighbors

    Returns:
        predictions: list of predicted labels
    """
    n_samples = X.shape[0]
    predictions = []

    for i in range(n_samples):
        # Compute distances to all other points
        distances = []
        for j in range(n_samples):
            if i == j:
                continue
            dist = _euclidean_distance(X[i], X[j])
            distances.append((dist, labels[j]))

        # Sort by distance, take k nearest
        distances.sort(key=lambda x: x[0])
        k_nearest = distances[:k]

        # Majority vote
        vote_counts = {}
        for _, label in k_nearest:
            vote_counts[label] = vote_counts.get(label, 0) + 1

        predicted = max(vote_counts, key=vote_counts.get)
        predictions.append(predicted)

    return predictions


# ===============================================================
# HELPER FUNCTIONS
# ===============================================================

def _euclidean_distance(a, b):
    """Euclidean distance between two numpy arrays."""
    return np.sqrt(np.sum((a - b) ** 2))


def _generate_crime_data(X, cluster_labels):
    """
    Generate synthetic crime rates for each node based on features.

    Logic:
    - Higher population density  more crime (crowded areas, more targets)
    - Higher industrial proximity  more crime (less surveillance, isolated)
    - Cluster effect: different clusters have different base rates

    Formula: crime_rate = 0.3*density + 0.5*industrial_prox + 0.2*cluster_factor + noise
    """
    n = X.shape[0]
    crime_rates = []

    # Assign cluster factors: cluster 0  0.3, cluster 1  0.6, cluster 2  0.9
    cluster_factors = {0: 0.3, 1: 0.6, 2: 0.9}

    for i in range(n):
        density = X[i, 0]
        industrial_prox = X[i, 1]
        cluster_factor = cluster_factors.get(int(cluster_labels[i]), 0.5)

        crime_rate = (0.3 * density +
                      0.5 * industrial_prox +
                      0.2 * cluster_factor +
                      random.gauss(0, 0.05))

        crime_rates.append(max(0.0, min(1.0, crime_rate)))  # clamp to [0, 1]

    return crime_rates


def _apply_risk_to_edges(graph):
    """
    Apply crime risk multipliers to all built road edges.
    For an edge (a, b), use the higher risk node's multiplier.
    """
    for edge_key, cost in list(graph.edges.items()):
        if cost >= float("inf"):
            continue  # skip blocked/non-existent roads

        a, b = edge_key
        risk_a = graph.nodes[a].crime_risk
        risk_b = graph.nodes[b].crime_risk

        mult_a = cfg.CRIME_RISK_MULTIPLIER.get(risk_a, 1.0)
        mult_b = cfg.CRIME_RISK_MULTIPLIER.get(risk_b, 1.0)
        multiplier = max(mult_a, mult_b)

        # Get base cost (without previous risk adjustment)
        base_cost = graph._default_edge_cost(a, b)
        graph.edges[edge_key] = base_cost * multiplier
