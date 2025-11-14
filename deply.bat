@echo off
REM Deploy SAC Centralized Agent
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.2 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.5 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.8 --gamma 3.0   --sim-start 0 --sim-end 720

python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.2 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.5 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC_CENTRALIZED  --lr 3e-4 --beta 0.8 --gamma 2.0   --sim-start 0 --sim-end 720

REM Deploy SAC Decentralized Agents
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.2 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.5 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.8 --gamma 3.0   --sim-start 0 --sim-end 720

python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.2 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.5 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type SAC  --lr 3e-4 --beta 0.8 --gamma 2.0   --sim-start 0 --sim-end 720

REM Deploy AAC-MADRL
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.2 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.5 --gamma 3.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.8 --gamma 3.0   --sim-start 0 --sim-end 720

python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.2 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.5 --gamma 2.0   --sim-start 0 --sim-end 720
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type AAC_MADRL  --lr 3e-4 --beta 0.8 --gamma 2.0   --sim-start 0 --sim-end 720

REM Deploy RBC
python -m deploy_model --dataset-anchor outputs/data/CA_20_dynamics/schema.json  --model-type RBC --lr 3e-4 --beta 0.2 --gamma 2.0 --sim-start 0 --sim-end 720