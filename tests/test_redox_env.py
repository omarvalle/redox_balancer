"""Quick tests for redox environment."""

import pytest
import numpy as np
from redox_balancer.env.redox_env import RedoxBalancerEnv
from cobra import Model, Reaction, Metabolite


def create_minimal_redox_model():
    """Create a minimal model for testing redox balance."""
    model = Model("minimal_redox")
    
    # Add metabolites
    glc_e = Metabolite("glc_e", compartment="e")
    glc_c = Metabolite("glc_c", compartment="c")
    g6p_c = Metabolite("g6p_c", compartment="c")
    f6p_c = Metabolite("f6p_c", compartment="c")
    fdp_c = Metabolite("fdp_c", compartment="c")
    gap_c = Metabolite("gap_c", compartment="c")
    pyr_c = Metabolite("pyr_c", compartment="c")
    
    # Redox metabolites
    nad_c = Metabolite("nad_c", compartment="c")
    nadh_c = Metabolite("nadh_c", compartment="c")
    h_c = Metabolite("h_c", compartment="c")
    
    # Energy metabolites
    atp_c = Metabolite("atp_c", compartment="c")
    adp_c = Metabolite("adp_c", compartment="c")
    pi_c = Metabolite("pi_c", compartment="c")
    
    # Biomass components
    biomass = Metabolite("biomass", compartment="c")
    
    model.add_metabolites([glc_e, glc_c, g6p_c, f6p_c, fdp_c, gap_c, pyr_c,
                          nad_c, nadh_c, h_c, atp_c, adp_c, pi_c, biomass])
    
    # Add reactions
    # Glucose uptake
    glc_uptake = Reaction("EX_glc_e")
    glc_uptake.add_metabolites({glc_e: -1})
    glc_uptake.bounds = (-10, 0)
    
    # Glucose transport
    glc_transport = Reaction("GLCt")
    glc_transport.add_metabolites({glc_e: -1, glc_c: 1})
    glc_transport.bounds = (-10, 10)
    
    # Simplified glycolysis with NADH production
    glycolysis = Reaction("GLYC")
    glycolysis.add_metabolites({
        glc_c: -1,
        nad_c: -2,
        adp_c: -2,
        pi_c: -2,
        pyr_c: 2,
        nadh_c: 2,
        h_c: 2,
        atp_c: 2
    })
    glycolysis.bounds = (0, 10)
    
    # Biomass reaction (consumes pyruvate and ATP)
    biomass_rxn = Reaction("BIOMASS")
    biomass_rxn.add_metabolites({
        pyr_c: -0.5,
        atp_c: -2,
        adp_c: 2,
        pi_c: 2,
        biomass: 1
    })
    biomass_rxn.bounds = (0, 10)
    
    # NADH exchange (for testing)
    nadh_exchange = Reaction("EX_nadh_c")
    nadh_exchange.add_metabolites({nadh_c: -1})
    nadh_exchange.bounds = (-10, 10)
    
    model.add_reactions([glc_uptake, glc_transport, glycolysis, biomass_rxn, nadh_exchange])
    
    # Set objective
    model.objective = "BIOMASS"
    
    return model


@pytest.fixture
def minimal_model():
    """Provide minimal test model."""
    return create_minimal_redox_model()


@pytest.fixture
def test_env(minimal_model):
    """Create test environment."""
    # Minimal enzyme database for testing
    enzyme_db = {
        "NOX_test": {
            "name": "Test NADH oxidase",
            "kcat": 100.0
        }
    }
    return RedoxBalancerEnv(
        base_model=minimal_model,
        agent_role="sink_designer",
        target_metabolite="NADH",
        max_steps=10,
        use_cache=False,
        enzyme_db=enzyme_db
    )


class TestRedoxEnv:
    """Test redox environment basic functionality."""
    
    def test_env_creation(self, test_env):
        """Test environment can be created."""
        assert test_env is not None
        assert test_env.target_metabolite == "NADH"
        assert test_env.agent_role == "sink_designer"
    
    def test_reset(self, test_env):
        """Test environment reset."""
        obs, info = test_env.reset()
        assert isinstance(obs, np.ndarray)
        assert obs.shape == (250,)
        assert test_env.steps == 0
    
    def test_step(self, test_env):
        """Test single environment step."""
        test_env.reset()
        
        # Simple action: small enzyme expression
        action = np.array([1, 0, 0, 0, 0])
        
        obs, reward, terminated, truncated, info = test_env.step(action)
        
        assert isinstance(obs, np.ndarray)
        assert isinstance(reward, float)
        assert isinstance(terminated, bool)
        assert isinstance(truncated, bool)
        assert isinstance(info, dict)
    
    def test_nadh_tracking(self, test_env):
        """Test NADH flux calculation."""
        test_env.reset()
        
        # Get baseline NADH flux
        baseline_flux = test_env.baseline_nadh
        assert baseline_flux is not None
        
        # After step, should be able to track NADH changes
        action = np.array([1, 0, 0, 0, 0])
        _, reward, _, _, info = test_env.step(action)
        
        # Reward should reflect NADH flux changes
        assert isinstance(info, dict)
    
    @pytest.mark.parametrize("target", ["NADH", "NAD+"])
    def test_target_metabolites(self, minimal_model, target):
        """Test different target metabolites."""
        enzyme_db = {"NOX_test": {"name": "Test NOX", "kcat": 100.0}}
        env = RedoxBalancerEnv(
            base_model=minimal_model,
            agent_role="sink_designer",
            target_metabolite=target,
            max_steps=5,
            enzyme_db=enzyme_db
        )
        
        obs, _ = env.reset()
        assert env.target_metabolite == target
        
        # Should complete without errors
        action = np.array([0, 0, 0, 0, 0])
        for _ in range(3):
            _, _, terminated, truncated, _ = env.step(action)
            if terminated or truncated:
                break


@pytest.mark.slow
class TestRedoxEnvIntegration:
    """Slower integration tests."""
    
    def test_full_episode(self, test_env):
        """Test full episode execution."""
        test_env.reset()
        
        total_reward = 0
        for i in range(test_env.max_steps):
            action = np.random.uniform(-0.1, 0.1, size=5)
            _, reward, terminated, truncated, _ = test_env.step(action)
            total_reward += reward
            
            if terminated or truncated:
                break
        
        assert i > 0  # Should run at least one step
        assert isinstance(total_reward, float)