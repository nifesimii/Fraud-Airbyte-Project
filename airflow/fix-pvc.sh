#!/bin/bash
cd deployments/airflow

echo "🔧 Fixing PVC access mode issue..."

# Step 1: Delete incorrect PVC
echo "Step 1: Deleting PVC with wrong access mode..."
kubectl delete pvc airflow-logs -n airflow 2>/dev/null || echo "PVC already deleted"

# Step 2: Create correct PVC
echo "Step 2: Creating PVC with ReadWriteOnce..."
cat > ../k8s/logs-pvc.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: airflow-logs
  namespace: airflow
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: local-path
EOF

kubectl apply -f ../k8s/logs-pvc.yaml

# Step 3: Wait for PVC to bind
echo "Step 3: Waiting for PVC to bind..."
kubectl wait --for=jsonpath='{.status.phase}'=Bound pvc/airflow-logs -n airflow --timeout=60s

# Step 4: Delete stuck pods
echo "Step 4: Deleting stuck pods..."
kubectl delete pod airflow-triggerer-0 -n airflow --force --grace-period=0 2>/dev/null || true
kubectl delete pod -n airflow -l tier=airflow --field-selector=status.phase=Pending --force --grace-period=0 2>/dev/null || true

# Step 5: Delete old replicasets
echo "Step 5: Cleaning up old replicasets..."
kubectl delete rs -n airflow airflow-scheduler-566d849b48 2>/dev/null || true
kubectl delete rs -n airflow airflow-dag-processor-7c76c74d8b 2>/dev/null || true
kubectl delete rs -n airflow airflow-api-server-546cc885c9 2>/dev/null || true

# Step 6: Wait for pods to restart
echo "Step 6: Waiting for pods to restart..."
sleep 60

# Step 7: Check status
echo ""
echo "✅ Current Status:"
kubectl get pods -n airflow

echo ""
echo "✅ PVC Status:"
kubectl get pvc -n airflow airflow-logs

echo ""
echo "If all pods are Running, you're good to go!"
echo "Access Airflow: make airflow-ui"