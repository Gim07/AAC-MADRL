# Train SAC Centralized Agent
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --central-agent --episodes 10 --lr 3e-4  --beta 0.2 --gamma 3.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --central-agent --episodes 10 --lr 3e-4  --beta 0.5 --gamma 3.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --central-agent --episodes 10 --lr 3e-4  --beta 0.8 --gamma 3.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off

python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --central-agent --episodes 10 --lr 3e-4  --beta 0.2 --gamma 2.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --central-agent --episodes 10 --lr 3e-4  --beta 0.5 --gamma 2.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --central-agent --episodes 10 --lr 3e-4  --beta 0.8 --gamma 2.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off

# Train SAC Decentralized Agents
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --episodes 10 --lr 3e-4  --beta 0.2 --gamma 3.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --episodes 10 --lr 3e-4  --beta 0.5 --gamma 3.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --episodes 10 --lr 3e-4  --beta 0.8 --gamma 3.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off

python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --episodes 10 --lr 3e-4  --beta 0.2 --gamma 2.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --episodes 10 --lr 3e-4  --beta 0.5 --gamma 2.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off
python -m train_sac --dataset-name data/CA_20_dynamics/schema.json --episodes 10 --lr 3e-4  --beta 0.8 --gamma 2.0 --hidden-dimension [256,256,256,256] --sim-start 0 --sim-end 720  --wandb off

# Train AAC-MADRL
python -m train_aac_madrl --dataset-name data/CA_20_dynamics/schema.json  --episodes 8 --lr 3e-4 --beta 0.2 --gamma 3.0  --sim-start 0 --sim-end 720  --wandb off
python -m train_aac_madrl --dataset-name data/CA_20_dynamics/schema.json  --episodes 8 --lr 3e-4 --beta 0.5 --gamma 3.0  --sim-start 0 --sim-end 720  --wandb off
python -m train_aac_madrl --dataset-name data/CA_20_dynamics/schema.json  --episodes 8 --lr 3e-4 --beta 0.8 --gamma 3.0  --sim-start 0 --sim-end 720  --wandb off

python -m train_aac_madrl --dataset-name data/CA_20_dynamics/schema.json  --episodes 8 --lr 3e-4 --beta 0.2 --gamma 2.0  --sim-start 0 --sim-end 720  --wandb off
python -m train_aac_madrl --dataset-name data/CA_20_dynamics/schema.json  --episodes 8 --lr 3e-4 --beta 0.5 --gamma 2.0  --sim-start 0 --sim-end 720  --wandb off
python -m train_aac_madrl --dataset-name data/CA_20_dynamics/schema.json  --episodes 8 --lr 3e-4 --beta 0.8 --gamma 2.0  --sim-start 0 --sim-end 720  --wandb off

# Deploy SAC Centralized Agent
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.2 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.5 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.8 --gamma 3.0   --sim-start 0 --sim-end 720

python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.2 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.5 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.8 --gamma 2.0   --sim-start 0 --sim-end 720

# Deploy SAC Decentralized Agents
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.2 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.5 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.8 --gamma 3.0   --sim-start 0 --sim-end 720

python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.2 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.5 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.8 --gamma 2.0   --sim-start 0 --sim-end 720

# Deploy AAC-MADRL
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.2 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.5 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.8 --gamma 3.0   --sim-start 0 --sim-end 720

python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.2 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.5 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.8 --gamma 2.0   --sim-start 0 --sim-end 720

# Deploy RBC
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type RBC --lr 3e-4 --beta 0.2 --gamma 2.0 --sim-start 0 --sim-end 720