# Demo video - narration transcript

Video: `MLOps_Assignment1_Pipeline_Demo.mp4` (6 min 36 s, 1080p, narrated, burned-in subtitles).
Every terminal scene shows real command output captured from this project; screenshots are from
the live MLflow UI, GitHub Actions, the Kubernetes cluster, Prometheus and Grafana.

## [00:00] Introduction

Hello everyone. My name is Altaf Anwar Pinjari, and my BITS ID is 2025AE05638. This is my submission for MLOps Assignment One. The goal is to predict the risk of heart disease from patient health data, and to take that model all the way to a cloud ready, monitored API. In the next few minutes I will walk you through the complete pipeline: the data and EDA, model training with MLflow, testing and CI/CD, Docker, Kubernetes, and finally monitoring. All the code is in my public GitHub repository, which you can see here.

## [00:34] Architecture

Here is the architecture. It has four layers. First, data and experimentation, where the UCI data is downloaded, cleaned and explored, and models are trained and tracked in MLflow. Second, a GitHub Actions pipeline that lints, tests, retrains and builds the container on every push. Third, the FastAPI service, packaged in Docker and deployed on Kubernetes. And fourth, monitoring, with Prometheus and Grafana.

## [01:00] 1. Data acquisition and cleaning

Let's start with the data. The download script pulls the Cleveland file from the UCI repository: three hundred and three patients, with thirteen clinical attributes. In the raw file, missing values are marked with a question mark. Only the CA and thal columns have them, six values in total. I keep them as missing in the cleaned CSV, and impute them inside the model pipeline. That way, exactly the same logic runs during training and at prediction time. The original target goes from zero to four, so I convert it into a simple yes or no for heart disease.

## [01:33] 1. Exploratory data analysis

In the EDA, the classes are fairly balanced: one hundred and sixty four healthy patients, and one hundred and thirty nine with heart disease. Patients with heart disease reach a lower maximum heart rate, and show more ST depression during exercise. Asymptomatic chest pain, a reversible thalassemia defect, and exercise induced angina all push the disease rate above sixty five percent. Because the maximum heart rate naturally drops with age, I engineered a new feature called the heart rate reserve ratio. It is the heart rate reached, divided by two hundred and twenty minus the age.

## [02:07] 2. Feature engineering and model development

The preprocessing is one single scikit-learn pipeline. It adds the engineered feature, imputes and scales the numeric columns, and one hot encodes the categorical codes. So thirteen raw inputs become twenty three model features. I trained three models: logistic regression, random forest, and gradient boosting. Each one is tuned with grid search and five fold stratified cross validation on the training split. That is sixty four configurations in total. The champion is chosen on cross validated ROC AUC, and the held out test set is used only for the final report, never for selection. Logistic regression won, with a cross validated ROC AUC of zero point nine zero seven. On the test set it reached zero point nine six one ROC AUC, and ninety three percent recall. For a screening model, recall is the number that matters most, because we do not want to miss sick patients.

## [03:00] 3. Experiment tracking with MLflow

Every experiment is tracked in MLflow. Each model family is a parent run, with its best parameters, its metrics, the plots, and the logged model. Inside it, every hyper parameter combination is a nested child run, so all sixty four configurations can be compared. This chart reads those runs back from MLflow. Here is the champion run, with its parameters and metrics, and here is the confusion matrix, logged as an artifact.

## [03:26] 4. Model packaging and reproducibility

For packaging, the final pipeline is saved both as a joblib file and in the MLflow model format, with its input signature. All library versions are pinned in requirements dot txt, and fixed random seeds make the training fully reproducible. Retraining from scratch gives exactly the same metrics.

## [03:43] 5. Automated testing

For quality, I wrote twenty eight unit tests with pytest. They cover data cleaning, feature engineering, the model, and the API, including invalid inputs that must be rejected. Flake8 reports zero issues, and all twenty eight tests pass.

## [04:00] 5. CI/CD pipeline with GitHub Actions

The GitHub Actions workflow has four chained jobs. Lint, then unit tests, then training, with a quality gate that fails the pipeline if the test ROC AUC drops below zero point eight five, and finally a Docker build with a smoke test. Because each job depends on the previous one, any error stops the pipeline with a clear log. Every run uploads the model, the test reports, the MLflow runs, and the Docker image as artifacts. In the smoke test, the container is started inside CI and the predict endpoint is called with a real sample. All runs on the main branch are green.

## [04:33] 6. FastAPI service and Docker

The API is built with FastAPI. The predict endpoint validates the JSON input with Pydantic, and returns the prediction, the label, the confidence, and the risk probability. The Dockerfile is a multi stage build on Python three point eleven slim. It runs as a non root user, and has a health check. Here I build the image, run the container, and send a sample patient. The model predicts heart disease, with ninety seven percent confidence.

## [04:59] 7. Deployment on Kubernetes

Next, deployment. I deployed to the Kubernetes cluster built into Docker Desktop, using one script that builds the image and applies all the manifests. The deployment runs two replicas, with readiness and liveness probes, and CPU and memory limits. It is exposed through a LoadBalancer on port eight zero eight zero, and through an NGINX Ingress for the host heart risk dot local. A horizontal pod autoscaler can scale it from two to five replicas. Calling the predict endpoint through the LoadBalancer, and through the Ingress, gives the same answer. A request without the right host header returns four zero four, which proves that the ingress routing works.

## [05:36] 8. Monitoring and logging

Finally, monitoring. Every request is logged as a structured JSON line with a request ID, and the API exposes Prometheus metrics for request counts, latency, prediction labels, and the risk distribution. To test it, I sent fifteen hundred requests with a load test, including some invalid ones. The autoscaler scaled the API up to five pods, and Prometheus automatically discovered and scraped every new pod. This query shows the request rate per pod, so you can see the traffic being shared across the replicas. In Grafana, we can see the request rate, the latency percentiles, zero server errors, and a positive prediction share of around forty six percent. That matches the prevalence in the training data, so there is no sign of data drift.

## [06:20] Summary

To summarize, this project gives a reproducible path from raw data to a monitored, autoscaled API, with tracked experiments, tested code, and a gated CI/CD pipeline. The code, the report, and all the screenshots are in my GitHub repository. Thank you for watching.
