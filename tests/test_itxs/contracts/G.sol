pragma solidity ^0.7.6;

contract G {
    uint256 public val;

    function setValue(uint256 v) public returns (uint256) {
        val = v;
        return val;
    }
}
