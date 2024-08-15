-- Generated from Simulink block 
library IEEE;
use IEEE.std_logic_1164.all;
library xil_defaultlib;
use xil_defaultlib.conv_pkg.all;
entity fft_12i_8192pt_18i18o_core_ip_struct is
  port (
    in0 : in std_logic_vector( 18-1 downto 0 );
    in1 : in std_logic_vector( 18-1 downto 0 );
    in2 : in std_logic_vector( 18-1 downto 0 );
    in3 : in std_logic_vector( 18-1 downto 0 );
    in4 : in std_logic_vector( 18-1 downto 0 );
    in5 : in std_logic_vector( 18-1 downto 0 );
    in6 : in std_logic_vector( 18-1 downto 0 );
    in7 : in std_logic_vector( 18-1 downto 0 );
    in8 : in std_logic_vector( 18-1 downto 0 );
    in9 : in std_logic_vector( 18-1 downto 0 );
    in10 : in std_logic_vector( 18-1 downto 0 );
    in11 : in std_logic_vector( 18-1 downto 0 );
    shift : in std_logic_vector( 16-1 downto 0 );
    sync : in std_logic_vector( 1 downto 0 );
    clk_1 : in std_logic;
    ce_1 : in std_logic;
    out0 : out std_logic_vector( 36-1 downto 0 );
    out1 : out std_logic_vector( 36-1 downto 0 );
    out2 : out std_logic_vector( 36-1 downto 0 );
    out3 : out std_logic_vector( 36-1 downto 0 );
    out4 : out std_logic_vector( 36-1 downto 0 );
    out5 : out std_logic_vector( 36-1 downto 0 );
    overflow : out std_logic_vector( 4-1 downto 0 );
    sync_out : out std_logic_vector( 1-1 downto 0 )
  );
end fft_12i_8192pt_18i18o_core_ip_struct;

architecture structural of fft_12i_8192pt_18i18o_core_ip_struct is
  component fft_12i_8192pt_18i18o_core_ip
    port (
      in0 : in std_logic_vector( 18-1 downto 0 );
      in1 : in std_logic_vector( 18-1 downto 0 );
      in2 : in std_logic_vector( 18-1 downto 0 );
      in3 : in std_logic_vector( 18-1 downto 0 );
      in4 : in std_logic_vector( 18-1 downto 0 );
      in5 : in std_logic_vector( 18-1 downto 0 );
      in6 : in std_logic_vector( 18-1 downto 0 );
      in7 : in std_logic_vector( 18-1 downto 0 );
      in8 : in std_logic_vector( 18-1 downto 0 );
      in9 : in std_logic_vector( 18-1 downto 0 );
      in10 : in std_logic_vector( 18-1 downto 0 );
      in11 : in std_logic_vector( 18-1 downto 0 );
      shift : in std_logic_vector( 16-1 downto 0 );
      sync : in std_logic_vector( 1-1 downto 0 );
      clk : in std_logic;
      out0 : out std_logic_vector( 36-1 downto 0 );
      out1 : out std_logic_vector( 36-1 downto 0 );
      out2 : out std_logic_vector( 36-1 downto 0 );
      out3 : out std_logic_vector( 36-1 downto 0 );
      out4 : out std_logic_vector( 36-1 downto 0 );
      out5 : out std_logic_vector( 36-1 downto 0 );
      overflow : out std_logic_vector( 4-1 downto 0 );
      sync_out : out std_logic_vector( 1-1 downto 0 )
    );
  end component;
begin
  fft_12i_8192pt_18i18o_core_ip_inst : fft_12i_8192pt_18i18o_core_ip
  port map (
    in0 => in0, 
    in1 => in1, 
    in2 => in2, 
    in3 => in3, 
    in4 => in4, 
    in5 => in5, 
    in6 => in6, 
    in7 => in7, 
    in8 => in8, 
    in9 => in9, 
    in10 => in10, 
    in11 => in11, 
    shift    => shift   , 
    sync     => sync    , 
    clk      => clk_1   , 
    out0     => out0    , 
    out1     => out1    , 
    out2     => out2    , 
    out3     => out3    , 
    out4     => out4    , 
    out5     => out5    , 
    overflow => overflow, 
    sync_out => sync_out 
  );
end structural; 
