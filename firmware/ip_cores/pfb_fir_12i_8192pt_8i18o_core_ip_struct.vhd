-- Generated from Simulink block 
library IEEE;
use IEEE.std_logic_1164.all;
library xil_defaultlib;
use xil_defaultlib.conv_pkg.all;
entity pfb_fir_12i_8192pt_8i18o_core_ip_struct is
  port (
    in0 : in std_logic_vector( 8-1 downto 0 );
    in1 : in std_logic_vector( 8-1 downto 0 );
    in2 : in std_logic_vector( 8-1 downto 0 );
    in3 : in std_logic_vector( 8-1 downto 0 );
    in4 : in std_logic_vector( 8-1 downto 0 );
    in5 : in std_logic_vector( 8-1 downto 0 );
    in6 : in std_logic_vector( 8-1 downto 0 );
    in7 : in std_logic_vector( 8-1 downto 0 );
    in8 : in std_logic_vector( 8-1 downto 0 );
    in9 : in std_logic_vector( 8-1 downto 0 );
    in10 : in std_logic_vector( 8-1 downto 0 );
    in11 : in std_logic_vector( 8-1 downto 0 );
    sync : in std_logic_vector( 1-1 downto 0 );
    sync_out : out std_logic_vector( 1-1 downto 0 );
    clk_1 : in std_logic;
    ce_1 : in std_logic;
    out0 : out std_logic_vector( 18-1 downto 0 );
    out1 : out std_logic_vector( 18-1 downto 0 );
    out2 : out std_logic_vector( 18-1 downto 0 );
    out3 : out std_logic_vector( 18-1 downto 0 );
    out4 : out std_logic_vector( 18-1 downto 0 );
    out5 : out std_logic_vector( 18-1 downto 0 );
    out6 : out std_logic_vector( 18-1 downto 0 );
    out7 : out std_logic_vector( 18-1 downto 0 );
    out8 : out std_logic_vector( 18-1 downto 0 );
    out9 : out std_logic_vector( 18-1 downto 0 );
    out10 : out std_logic_vector( 18-1 downto 0 );
    out11 : out std_logic_vector( 18-1 downto 0 )
  );
end pfb_fir_12i_8192pt_8i18o_core_ip_struct;

architecture structural of pfb_fir_12i_8192pt_8i18o_core_ip_struct is
  component pfb_fir_12i_8192pt_8i18o_core_ip
    port ( 
      in0 : in std_logic_vector( 8-1 downto 0 );
      in1 : in std_logic_vector( 8-1 downto 0 );
      in2 : in std_logic_vector( 8-1 downto 0 );
      in3 : in std_logic_vector( 8-1 downto 0 );
      in4 : in std_logic_vector( 8-1 downto 0 );
      in5 : in std_logic_vector( 8-1 downto 0 );
      in6 : in std_logic_vector( 8-1 downto 0 );
      in7 : in std_logic_vector( 8-1 downto 0 );
      in8 : in std_logic_vector( 8-1 downto 0 );
      in9 : in std_logic_vector( 8-1 downto 0 );
      in10 : in std_logic_vector( 8-1 downto 0 );
      in11 : in std_logic_vector( 8-1 downto 0 );
      sync : in std_logic_vector( 1-1 downto 0 );
      sync_out : out std_logic_vector( 1-1 downto 0 );
      out0 : out std_logic_vector( 18-1 downto 0 );
      out1 : out std_logic_vector( 18-1 downto 0 );
      out2 : out std_logic_vector( 18-1 downto 0 );
      out3 : out std_logic_vector( 18-1 downto 0 );
      out4 : out std_logic_vector( 18-1 downto 0 );
      out5 : out std_logic_vector( 18-1 downto 0 );
      out6 : out std_logic_vector( 18-1 downto 0 );
      out7 : out std_logic_vector( 18-1 downto 0 );
      out8 : out std_logic_vector( 18-1 downto 0 );
      out9 : out std_logic_vector( 18-1 downto 0 );
      out10 : out std_logic_vector( 18-1 downto 0 );
      out11 : out std_logic_vector( 18-1 downto 0 );
      clk : in std_logic
    );
  end component;
begin
  pfb_fir_12i_8192pt_8i18o_core_ip_inst : pfb_fir_12i_8192pt_8i18o_core_ip  
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
    sync     => sync,      
    sync_out  => sync_out,  
    clk      => clk_1,       
    out0 => out0, 
    out1 => out1, 
    out2 => out2, 
    out3 => out3, 
    out4 => out4, 
    out5 => out5, 
    out6 => out6, 
    out7 => out7, 
    out8 => out8,
    out9 => out9,
    out10 => out10,
    out11 => out11
  );
end structural;
