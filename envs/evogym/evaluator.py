import os
import numpy as np

from gym_utils import make_vec_envs


class EvogymControllerEvaluator:
    def __init__(self, env_id, robot, num_eval=1):
        self.env_id = env_id
        self.robot = robot
        self.num_eval = num_eval

    def evaluate_controller(self, key, controller, generation):
        env = make_vec_envs(self.env_id, self.robot, 0, 1)

        obs = env.reset()
        episode_rewards = []
        while len(episode_rewards) < self.num_eval:
            # t = env.env_method('get_time')[0]
            action = np.array(controller.activate(obs[0]))*2 - 1
            obs, _, done, infos = env.step([np.array(action)])

            if 'episode' in infos[0]:
                # print(t)
                reward = infos[0]['episode']['r']
                episode_rewards.append(reward)

        env.close()

        results = {
            'fitness': np.mean(episode_rewards),
        }
        return results


class EvogymControllerEvaluatorNS:
    def __init__(self, env_id, robot, num_eval=1):
        self.env_id = env_id
        self.robot = robot
        self.num_eval = num_eval

    def evaluate_controller(self, key, controller, generation):
        env = make_vec_envs(self.env_id, self.robot, 0, 1)

        obs = env.reset()

        obs_data = []
        act_data = []

        episode_rewards = []
        episode_data = []
        while len(episode_rewards) < self.num_eval:
            action = np.array(controller.activate(obs[0]))*2 - 1
            obs_data.append(obs)
            act_data.append(action)
            obs, _, done, infos = env.step([np.array(action)])

            if 'episode' in infos[0]:
                obs_data = np.vstack(obs_data)
                obs_cov = self.calc_covar(obs_data)

                act_data = np.clip(np.vstack(act_data),-1,1)
                act_cov = self.calc_covar(act_data, align=False)

                data = np.hstack([obs_cov,act_cov])
                episode_data.append(data)

                obs_data = []
                act_data = []

                reward = infos[0]['episode']['r']
                episode_rewards.append(reward)

        env.close()

        results = {
            'reward': np.mean(episode_rewards),
            'data': np.mean(np.vstack(episode_data),axis=0)
        }
        return results

    @staticmethod
    def calc_covar(vec, align=True):
        ave = np.mean(vec,axis=0)
        if align:
            vec_align = (vec-ave).T
        else:
            vec_align = vec.T
        comb_indices = np.tril_indices(vec.shape[1],k=0)
        covar = np.mean(vec_align[comb_indices[0]]*vec_align[comb_indices[1]],axis=1)
        return covar


from run_ppo import run_ppo

class EvogymStructureEvaluator:
    def __init__(self, env_id, save_path, ppo_iters, eval_interval, deterministic=False):
        self.env_id = env_id
        self.save_path = save_path
        self.robot_save_path = os.path.join(save_path, 'robot')
        self.controller_save_path = os.path.join(save_path, 'controller')
        self.ppo_iters = ppo_iters
        self.eval_interval = eval_interval
        self.deterministic = deterministic

        os.makedirs(self.robot_save_path, exist_ok=True)
        os.makedirs(self.controller_save_path, exist_ok=True)

    def evaluate_structure(self, key, robot, generation):

        file_robot = os.path.join(self.robot_save_path, f'{key}')
        file_controller = os.path.join(self.controller_save_path, f'{key}')
        np.savez(file_robot, **robot)

        fitness = run_ppo(
            env_id=self.env_id,
            robot=robot,
            train_iters=self.ppo_iters,
            eval_interval=self.eval_interval,
            save_file=file_controller,
            deterministic=self.deterministic
        )

        results = {
            'fitness': fitness,
        }
        return results

class EvogymStructureEvaluatorME:
    def __init__(self, env_id, save_path, ppo_iters, eval_interval, bd_dictionary, deterministic=False):
        self.env_id = env_id
        self.save_path = save_path
        self.robot_save_path = os.path.join(save_path, 'robot')
        self.controller_save_path = os.path.join(save_path, 'controller')
        self.ppo_iters = ppo_iters
        self.eval_interval = eval_interval
        self.bd_dictionary = bd_dictionary
        self.deterministic = deterministic

        os.makedirs(self.robot_save_path, exist_ok=True)
        os.makedirs(self.controller_save_path, exist_ok=True)

    def evaluate_structure(self, key, robot, generation):

        file_robot = os.path.join(self.robot_save_path, f'{key}')
        file_controller = os.path.join(self.controller_save_path, f'{key}')
        np.savez(file_robot, **robot)

        fitness = run_ppo(
            env_id=self.env_id,
            robot=robot,
            train_iters=self.ppo_iters,
            eval_interval=self.eval_interval,
            save_file=file_controller,
            deterministic=self.deterministic
        )
        bd = {bd_name: bd_func.evaluate(robot) for bd_name,bd_func in self.bd_dictionary.items()}

        results = {
            'fitness': fitness,
            'bd': bd
        }
        return results
